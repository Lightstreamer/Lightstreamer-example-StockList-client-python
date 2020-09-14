#!/usr/bin/python

#  Copyright (c) Lightstreamer Srl.
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

import sys
import logging
import threading
import time
import traceback

# Modules aliasing and function utilities to support a
# very coarse version differentiation between Python 2 and Python 3.
PY3 = sys.version_info[0] == 3
PY2 = sys.version_info[0] == 2

if PY3:
    from urllib.request import urlopen as _urlopen
    from urllib.parse import (urlparse as parse_url, urljoin, urlencode)

    def _url_encode(params):
        return urlencode(params).encode("utf-8")

    def _iteritems(d):
        return iter(d.items())

    def wait_for_input():
        input("{0:-^80}\n".format("HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM \
LIGHTSTREAMER"))

else:
    from urllib import (urlopen as _urlopen, urlencode)
    from urlparse import urlparse as parse_url
    from urlparse import urljoin

    def _url_encode(params):
        return urlencode(params)

    def _iteritems(d):
        return d.iteritems()

    def wait_for_input():
        raw_input("{0:-^80}\n".format("HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM \
LIGHTSTREAMER"))
CONNECTION_URL_PATH = "lightstreamer/create_session.txt"
BIND_URL_PATH = "lightstreamer/bind_session.txt"
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
        Lightstreamer Text Protocol specifications.
        """
        if value == "$":
            return u''
        elif value == "#":
            return None
        elif not value:
            return last
        elif value[0] in "#$":
            value = value[1:]

        return value

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
        self._base_url = parse_url(base_url)
        self._adapter_set = adapter_set
        self._user = user
        self._password = password
        self._session = {}
        self._subscriptions = {}
        self._current_subscription_key = 0
        self._stream_connection = None
        self._stream_connection_thread = None
        self._bind_counter = 0

    def _encode_params(self, params):
        """Encode the parameter for HTTP POST submissions, but
        only for non empty values..."""
        return _url_encode(
            dict([(k, v) for (k, v) in _iteritems(params) if v])
        )

    def _call(self, base_url, url, params):
        """Open a network connection and performs HTTP Post
        with provided params.
        """
        # Combines the "base_url" with the
        # required "url" to be used for the specific request.
        url = urljoin(base_url.geturl(), url)
        body = self._encode_params(params)
        log.debug("Making a request to <%s> with body <%s>", url, body)
        return _urlopen(url, data=body)

    def _set_control_link_url(self, custom_address=None):
        """Set the address to use for the Control Connection
        in such cases where Lightstreamer is behind a Load Balancer.
        """
        if custom_address is None:
            self._control_url = self._base_url
        else:
            parsed_custom_address = parse_url("//" + custom_address)
            self._control_url = parsed_custom_address._replace(
                scheme=self._base_url[0]
            )

    def _control(self, params):
        """Create a Control Connection to send control commands
        that manage the content of Stream Connection.
        """
        params["LS_session"] = self._session["SessionId"]
        response = self._call(self._control_url, CONTROL_URL_PATH, params)
        decoded_response = response.readline().decode("utf-8").rstrip()
        log.debug("Server response: <%s>", decoded_response)
        return decoded_response

    def _read_from_stream(self):
        """Read a single line of content of the Stream Connection."""
        line = self._stream_connection.readline().decode("utf-8").rstrip()
        return line

    def connect(self):
        """Establish a connection to Lightstreamer Server to create a new
        session.
        """
        log.debug("Opening a new session to <%s>", self._base_url.geturl())
        self._stream_connection = self._call(
            self._base_url,
            CONNECTION_URL_PATH,
            {
             "LS_op2": 'create',
             "LS_cid": 'mgQkwtwdysogQz2BJ4Ji kOj2Bg',
             "LS_adapter_set": self._adapter_set,
             "LS_user": self._user,
             "LS_password": self._password}
        )
        stream_line = self._read_from_stream()
        self._handle_stream(stream_line)

    def bind(self):
        """Replace a completely consumed connection in listening for an active
        Session.
        """
        log.debug("Binding to <%s>", self._control_url.geturl())
        self._stream_connection = self._call(
            self._control_url,
            BIND_URL_PATH,
            {
             "LS_session": self._session["SessionId"]
             }
        )

        self._bind_counter += 1
        stream_line = self._read_from_stream()
        self._handle_stream(stream_line)
        log.info("Bound to <%s>", self._control_url.geturl())

    def _handle_stream(self, stream_line):
        if stream_line == OK_CMD:
            log.info("Successfully connected to <%s>", self._base_url.geturl())
            log.debug("Starting to handling real-time stream")
            # Parsing session inkion
            while 1:
                next_stream_line = self._read_from_stream()
                if next_stream_line:
                    session_key, session_value = next_stream_line.split(":", 1)
                    self._session[session_key] = session_value
                else:
                    break

            # Setup of the control link url
            self._set_control_link_url(self._session.get("ControlAddress"))

            # Start a new thread to handle real time updates sent
            # by Lightstreamer Server on the stream connection.
            self._stream_connection_thread = threading.Thread(
                name="StreamThread-{0}".format(self._bind_counter),
                target=self._receive
            )
            self._stream_connection_thread.setDaemon(True)
            self._stream_connection_thread.start()
            log.info("Started handling of real-time stream")
        else:
            lines = self._stream_connection.readlines()
            lines.insert(0, stream_line)

            log.error("\nServer response error: \n%s", "".join([str(line) for line in lines]))
            raise IOError()

    def _join(self):
        """Await the natural StreamThread termination."""
        if self._stream_connection_thread:
            log.debug("Waiting for thread to terminate")
            self._stream_connection_thread.join()
            self._stream_connection_thread = None
            log.debug("Thread terminated")

    def disconnect(self):
        """Request to close the session previously opened with the connect()
        invocation.
        """
        if self._stream_connection is not None:
            log.debug("Closing session to <%s>", self._base_url.geturl())
            server_response = self._control({"LS_op": OP_DESTROY})
            # There is no need to explicitly close the connection, since it is
            # handled by thread completion.
            self._join()
            log.info("Closed session to <%s>", self._base_url.geturl())
        else:
            log.warning("No connection to Lightstreamer")

    def subscribe(self, subscription):
        """"Perform a subscription request to Lightstreamer Server."""
        # Register the Subscription with a new subscription key
        self._current_subscription_key += 1
        self._subscriptions[self._current_subscription_key] = subscription

        # Send the control request to perform the subscription
        log.debug("Making a new subscription request")
        server_response = self._control({
            "LS_table": self._current_subscription_key,
            "LS_op": OP_ADD,
            "LS_data_adapter": subscription.adapter,
            "LS_mode": subscription.mode,
            "LS_schema": " ".join(subscription.field_names),
            "LS_id": " ".join(subscription.item_names),
        })
        if server_response == OK_CMD:
            log.info("Successfully subscribed ")
        else:
            log.warning("Subscription error")
        return self._current_subscription_key

    def unsubscribe(self, subcription_key):
        """Unregister the Subscription associated with the
        specified subscription_key.
        """
        log.debug("Making an unsubscription request")
        if subcription_key in self._subscriptions:
            server_response = self._control({
                "LS_Table": subcription_key,
                "LS_op": OP_DELETE
            })

            if server_response == OK_CMD:
                del self._subscriptions[subcription_key]
                log.info("Successfully unsubscribed")
            else:
                log.warning("Unsubscription error")
        else:
            log.warning("No subscription key %s found!", subcription_key)

    def _forward_update_message(self, update_message):
        """Forwards the real time update to the relative
        Subscription instance for further dispatching to its listeners.
        """
        log.debug("Received update message: <%s>", update_message)
        try:
            tok = update_message.split(',', 1)
            table, item = int(tok[0]), tok[1]
            if table in self._subscriptions:
                self._subscriptions[table].notifyupdate(item)
            else:
                log.warning("No subscription found!")
        except Exception:
            print(traceback.format_exc())

    def _receive(self):
        rebind = False
        receive = True
        while receive:
            log.debug("Waiting for a new message")
            try:
                message = self._read_from_stream()
                log.debug("Received message: <%s>", message)
                if not message.strip():
                    message = None
            except Exception:
                log.error("Communication error")
                print(traceback.format_exc())
                message = None

            if message is None:
                receive = False
                log.warning("No new message received")
            elif message == PROBE_CMD:
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
                rebind = True
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
                self._forward_update_message(message)

        if not rebind:
            log.debug("No rebind to <%s>, clearing internal session data",
                      self._base_url.geturl())
            # Clear internal data structures for session
            # and subscriptions management.
            self._stream_connection = None
            self._session.clear()
            self._subscriptions.clear()
            self._current_subscription_key = 0
        else:
            log.debug("Binding to this active session")
            self.bind()

logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(levelname)-7s ' +
                    '%(threadName)-15s %(message)s', level=logging.INFO)

# Establishing a new connection to Lightstreamer Server
print("Starting connection")
# lightstreamer_client = LSClient("http://localhost:8080", "DEMO")
lightstreamer_client = LSClient("http://push.lightstreamer.com", "DEMO")
try:
    lightstreamer_client.connect()
except Exception as e:
    print("Unable to connect to Lightstreamer Server")
    print(traceback.format_exc())
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

wait_for_input()

# Unsubscribing from Lightstreamer by using the subscription key
lightstreamer_client.unsubscribe(sub_key)

# Disconnecting
lightstreamer_client.disconnect()
