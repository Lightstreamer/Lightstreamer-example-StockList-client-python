#!/usr/bin/python

#  Copyright 2014 Weswit s.r.l.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import urlparse
import urllib
import logging
import threading
import sys
import time

CONNECTION_URL_PATH = "lightstreamer/create_session.txt"
CONTROL_URL_PATH = "lightstreamer/control.txt"

# Request parameter to create and activate a new Table.
OP_ADD = "add"

# Request parameter to delete a previously created Table.
OP_DELETE = "delete"

# Request parameter to force closure of an existing session.
OP_DESTROY = "destroy"

# List of possible server responses
PROBE_CMD = "PROBE"
END_CMD = "END"
LOOP_CMD = "LOOP"
ERROR_CMD = "ERROR"
SYNC_ERROR_CMD = "SYNC ERROR"
OK_CMD = "OK"

log = logging.getLogger()


class Subscription(object):
    """Represents a Subscription to be submitted to a Lightstreamer Server."""

    def __init__(self, mode, items, fields, adapter=""):
        self.item_names = items
        self._items_map = {}
        self.field_names = fields
        self.adapter = adapter
        self.mode = mode
        self.snapshot = "true"
        self._listeners = []

    def _decode(self, value, last):
        """Decode the field value according to
        Lightstremar Text Protocol specifications.
        """
        if value == "$":
            return u''
        elif value == "#":
            return None
        elif not value:
            return last
        elif value[0] in "#$":
            value = value[1:]

        return str(value.decode("unicode_escape"))

    def addlistener(self, listener):
        self._listeners.append(listener)

    def notifyupdate(self, item_line):
        """Invoked by LSClient each time Lightstreamer Server pushes
        a new item event.
        """
        # Tokenize the item line as sent by Lightstreamer
        toks = item_line.rstrip('\r\n').split('|')
        undecoded_item = dict(list(zip(self.field_names, toks[1:])))

        # Retrieve the previous item stored into the map, if present.
        # Otherwise create a new empty dict.
        item_pos = int(toks[0])
        curr_item = self._items_map.get(item_pos, {})
        # Update the map with new values, merging with the
        # previous ones if any.
        self._items_map[item_pos] = dict([
            (k, self._decode(v, curr_item.get(k))) for k, v
            in list(undecoded_item.items())
        ])
        # Make an item info as a new event to be passed to listeners
        item_info = {
            'pos': item_pos,
            'name': self.item_names[item_pos - 1],
            'values': self._items_map[item_pos]
        }

        # Update each registered listener with new event
        for on_item_update in self._listeners:
            on_item_update(item_info)


class LSClient(object):
    """Manages the communication with Lightstreamer Server"""

    def __init__(self, base_url, adapter_set="", user="", password=""):
        self._base_url = urlparse.urlparse(base_url)
        self._adapter_set = adapter_set
        self._user = user
        self._password = password
        self._session = {}
        self._subscriptions = {}
        self._current_subscription_key = 0
        self._stream_connection = None
        self._stream_connection_thread = None

    def _encode_params(self, params):
        """Encode the parameter for HTTP POST submissions, but
        only for non empty values..."""
        return urllib.urlencode(
            dict([(k, v) for (k, v) in params.iteritems() if v])
        )

    def _call(self, base_url, url, body):
        """Open a network connection and performs HTTP Post
        with provided body.
        """
        # Combines the "base_url" with the
        # required "url" to be used for the specific request.
        url = urlparse.urljoin(base_url.geturl(), url)
        return urllib.urlopen(url, data=self._encode_params(body))

    def _set_control_link_url(self, custom_address=None):
        """Set the address to use for the Control Connection
        in such cases where Lightstreamer is behind a Load Balancer.
        """
        if custom_address is None:
            self._control_url = self._base_url
        else:
            parsed_custom_address = urlparse.urlparse("//" + custom_address)
            self._control_url = parsed_custom_address._replace(
                scheme=self._base_url[0]
            )

    def _control(self, params):
        params["LS_session"] = self._session["SessionId"]
        return self._call(self._control_url, CONTROL_URL_PATH, params)

    def connect(self):
        """Establish a connection to Lightstreamer Server to create
        a new session.
        """

        self._stream_connection = self._call(
            self._base_url,
            CONNECTION_URL_PATH,
            {"LS_adapter_set": self._adapter_set,
             "LS_user": self._user,
             "LS_password": self._password}
        )
        server_response = self._stream_connection.readline().rstrip()
        if server_response == OK_CMD:
            # Parsing session information
            while 1:
                line = self._stream_connection.readline().rstrip()
                if line:
                    session_key, session_value = line.split(":", 1)
                    self._session[session_key] = session_value
                else:
                    break

            # Setup of the control link url
            self._set_control_link_url(self._session.get("ControlAddress"))

            # Start a new thread to handle real time updates sent
            # by Lightstreamer Server on the stream connection.
            self._stream_connection_thread = threading.Thread(
                name="STREAM-CONN-THREAD",
                target=self._receive
            )
            self._stream_connection_thread.setDaemon(True)
            self._stream_connection_thread.start()
        else:
            lines = self._stream_connection.readlines()
            lines.insert(0, server_response)
            log.error("Server response error: \n%s" % "".join(lines))
            raise IOError()

    def _join(self):
        """Await the natural STREAM-CONN-THREAD termination."""
        if self._stream_connection_thread:
            log.debug("Waiting for STREAM-CONN-THREAD to terminate")
            self._stream_connection_thread.join()
            self._stream_connection_thread = None
            log.debug("STREAM-CONN-THREAD terminated")

    def disconnect(self):
        """Request to close the session previously opened with
        the connect() invocation.
        """
        if self._stream_connection is not None:
            # Close the HTTP connection
            self._stream_connection.close()
            log.debug("Connection closed")
            self._join()
            print("DISCONNECTED FROM LIGHTSTREAMER")
        else:
            log.warning("No connection to Lightstreamer")

    def destroy(self):
        """Destroy the session previously opened with
        the connect() invocation.
        """
        if self._stream_connection is not None:
            control_connection = self._control({"LS_op": OP_DESTROY})
            server_response = control_connection.readline().rstrip()
            if server_response == OK_CMD:
                # There is no need to explicitly close the connection,
                # since it is handled by thread completion.
                self._join()
            else:
                log.warning("No connection to Lightstreamer")

    def subscribe(self, subscription):
        """"Perform a subscription request to Lightstreamer Server."""
        # Register the Subscription with a new subscription key
        self._current_subscription_key += 1
        self._subscriptions[self._current_subscription_key] = subscription

        # Send the control request to perform the subscription
        self._control({
            "LS_Table": self._current_subscription_key,
            "LS_op": OP_ADD,
            "LS_data_adapter": subscription.adapter,
            "LS_mode": subscription.mode,
            "LS_schema": " ".join(subscription.field_names),
            "LS_id": " ".join(subscription.item_names),
        })
        return self._current_subscription_key

    def unsubscribe(self, subcription_key):
        """Unregister the Subscription associated to the
        specified subscription_key.
        """
        if subcription_key in self._subscriptions:
            control_connection = self._control({
                "LS_Table": subcription_key,
                "LS_op": OP_DELETE
            })
            server_response = control_connection.readline()

            if server_response.rstrip() == OK_CMD:
                del self._subscriptions[subcription_key]
                log.info("Unsubscription successfull")
            else:
                log.warning("Server error")
        else:
            log.warning("No subscription key %d found!" % subcription_key)

    def _forward_update_message(self, update_message):
        """Forwards the real time update to the relative
        Subscription instance for further dispatching to its listeners.
        """
        tok = update_message.split(',')
        table, item = int(tok[0]), tok[1]
        if table in self._subscriptions:
            self._subscriptions[table].notifyupdate(item)
        else:
            log.warning("No subscription found!")

    def _receive(self):
        receive = True
        while receive:
            log.debug("Waiting for a new message")
            try:
                message = self._stream_connection.readline()
                log.debug("Received message - %s" % message)
            except Exception:
                message = None

            if message is None:
                receive = False
                log.warning("No new message received")
            elif message.startswith(PROBE_CMD):
                # Skipping the PROBE message, keep on receiving messages.
                log.debug("PROBE message")
            elif message.startswith(ERROR_CMD):
                # Terminate the receiving loop on ERROR message
                receive = False
                log.error("ERROR")
            elif message.startswith(LOOP_CMD):
                # Terminate the the receiving loop on LOOP message.
                # A complete implementation should proceed with
                # a rebind of the session.
                log.debug("LOOP")
                receive = False
            elif message.startswith(SYNC_ERROR_CMD):
                # Terminate the receiving loop on SYNC ERROR message.
                # A complete implementation should create a new session
                # and re-subscribe to all the old items and relative fields.
                log.error("SYNC ERROR")
                receive = False
            elif message.startswith(END_CMD):
                # Terminate the receiving loop on END message.
                # The session has been forcibly closed on the server side.
                # A complete implementation should handle the
                # "cause_code" if present.
                log.info("Connection closed by the server")
                receive = False
            elif message.startswith("Preamble"):
                # Skipping Preamble message, keep on receiving messages.
                log.debug("Preamble")
            else:
                self._forward_update_message(message.rstrip())

        # Clear internal data structures for session
        # and subscriptions management.
        self._stream_connection.close()
        self._stream_connection = None
        self._session.clear()
        self._subscriptions.clear()
        self._current_subscription_key = 0

logging.basicConfig(level=logging.INFO)

# Establishing a new connection to Lightstreamer Server
lightstreamer_client = LSClient("http://push.lightstreamer.com:80", "DEMO")
try:
    lightstreamer_client.connect()
except Exception as e:
    print("Unable to connect to Lightstreamer Server")
    sys.exit(1)


# Making a new Subscription in MERGE mode
subscription = Subscription(
    mode="MERGE",
    items=["item1", "item2", "item3", "item4",
           "item5", "item6", "item7", "item8",
           "item9", "item10", "item11", "item12"],
    fields=["stock_name", "last_price", "time", "bid", "ask"],
    adapter="QUOTE_ADAPTER")


# A simple function acting as a Subscription listener
def on_item_update(item_update):
    print("{stock_name:<19}: Last{last_price:>6} - Time {time:<8} - "
          "Bid {bid:>5} - Ask {ask:>5}".format(**item_update["values"]))

# Adding the "on_item_update" function to Subscription
subscription.addlistener(on_item_update)

# Registering the Subscription
sub_key = lightstreamer_client.subscribe(subscription)

raw_input("{0:-^80}\n".format("HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM \
LIGHTSTREAMER"))

# Unsubscribing from Lightstreamer by using the subscription key
lightstreamer_client.unsubscribe(sub_key)

# Disconnecting
lightstreamer_client.disconnect()
time.sleep(4)
