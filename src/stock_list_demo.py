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

from lightstreamer.client import *
from subscription_listener import *

def wait_for_input():
    input("{0:-^80}\n".format("HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM LIGHTSTREAMER"))

loggerProvider = ConsoleLoggerProvider(ConsoleLogLevel.WARN)
LightstreamerClient.setLoggerProvider(loggerProvider)

# Establishing a new connection to Lightstreamer Server
# lightstreamer_client = LightstreamerClient("http://localhost:8080", "DEMO")
lightstreamer_client = LightstreamerClient("http://push.lightstreamer.com", "DEMO")
lightstreamer_client.connect()

# Making a new Subscription in MERGE mode
subscription = Subscription(
    mode="MERGE",
    items=["item1", "item2", "item3", "item4",
           "item5", "item6", "item7", "item8",
           "item9", "item10", "item11", "item12"],
    fields=["stock_name", "last_price", "time", "bid", "ask"])
subscription.setDataAdapter("QUOTE_ADAPTER")

# Adding the subscription listener to get notifications about new updates
subscription.addListener(SubListener())

# Registering the Subscription
lightstreamer_client.subscribe(subscription)

wait_for_input()

# Unsubscribing from Lightstreamer by using the subscription as key
lightstreamer_client.unsubscribe(subscription)

# Disconnecting
lightstreamer_client.disconnect()
