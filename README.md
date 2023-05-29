# Lightstreamer - Basic Stock-List Demo - Python Client

This project contains an example of a Python application that employs the **Lightstreamer Python Client library**.

![screenshot](screen_python_large.png)

## Details

The example provides a very simple version of the [Stock-List Demos](https://github.com/Lightstreamer/Lightstreamer-example-Stocklist-client-javascript), where a single subscription to 12 items is submitted.
The updates are then formatted and displayed on the console.
  
The script shows all the basic steps required to establish an interaction to Lightstreamer Server. More specifically, the code comprises these actions: 

* Connection to Lightstreamer server and session creation
* Subscription to items with specified fields
* Notification about real time updates
* Unsubscription from items
* Final disconnection 

## Install

If you want to install a version of this demo pointing to your local Lightstreamer Server, follow these steps:

* Note that, as prerequisite, the [Lightstreamer - Stock- List Demo - Java Adapter](https://github.com/Lightstreamer/Lightstreamer-example-Stocklist-adapter-java) has to be deployed on your local Lightstreamer Server instance. Please check out that project and follow the installation instructions provided with it.
* Launch Lightstreamer Server.
* Go to [http://python.org/download/](http://python.org/download/) and download the appropriate **Python** (tested since version 3.9) for your OS and follow the instructions to install it on your system. Note that the demo currently **can not** be launched from IDLE.
* Install the latest version of the _Lightstreamer Python Client library_ from [PyPi](https://pypi.org/project/lightstreamer-client-lib/): `python -m pip install lightstreamer-client-lib`

You can now run the Python script simply executing the following commands on different OS:
	
* Windows machines:

```
start python /path/to/example/stock_list_demo.py
```

* Linux machines: 

```
python /path/to/example/stock_list_demo.py
```
or, alternatively, you can make the script executable:

```
chmod +x /path/to/example/stock_list_demo.py
```

and then type:
```
/path/to/example/stock_list_demo.py
```

The example is configured to connect to http://push.lightstreamer.com:80, but you can easily change these settings modifying the following line:

```lightstreamer_client = LightstreamerClient("http://push.lightstreamer.com:80", "DEMO")```

to connect to the correct combination of host and port of your Lightstreamer server.

### Lightstreamer Adapters Needed by this Demo Client

<!-- START RELATED_ENTRIES -->
* [Lightstreamer - Stock- List Demo - Java Adapter](https://github.com/Lightstreamer/Lightstreamer-example-Stocklist-adapter-java)

<!-- END RELATED_ENTRIES -->

### Related Projects

* [Demos](https://demos.lightstreamer.com)
* [Lightstreamer - Stock-List Demos - HTML Clients](https://github.com/Lightstreamer/Lightstreamer-example-Stocklist-client-javascript)
* [Lightstreamer - Basic Stock-List Demo - jQuery (jqGrid) Client](https://github.com/Lightstreamer/Lightstreamer-example-StockList-client-jquery)
* [Lightstreamer - Stock-List Demo - Dojo Toolkit Client](https://github.com/Lightstreamer/Lightstreamer-example-StockList-client-dojo)
* [Lightstreamer - Basic Stock-List Demo - Java SE (Swing) Client](https://github.com/Lightstreamer/Lightstreamer-example-StockList-client-java)
* [Lightstreamer - Basic Stock-List Demo - .NET Client](https://github.com/Lightstreamer/Lightstreamer-example-StockList-client-dotnet)

## Lightstreamer Compatibility Notes

* Compatible with Lightstreamer Python Client SDK 1.0 or newer.
* Compatible with Lightstreamer Server since version 7.3.2.