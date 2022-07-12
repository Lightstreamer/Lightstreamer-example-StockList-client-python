# A class implementing the SubscriptionListener interface
class SubListener:
  def onItemUpdate(self, update):
    print("{stock_name:<19}: Last{last_price:>6} - Time {time:<8} - "
          "Bid {bid:>5} - Ask {ask:>5}".format(
            stock_name=update.getValue("stock_name"),
            last_price=update.getValue("last_price"),
            time=update.getValue("time"),
            bid=update.getValue("bid"),
            ask=update.getValue("ask")))  
    pass
  def onListenStart(self, aSub):
    pass
  def onClearSnapshot(self, itemName, itemPos):
    pass
  def onCommandSecondLevelItemLostUpdates(self, lostUpdates, key):
    pass
  def onCommandSecondLevelSubscriptionError(self, code, message, key):
    pass
  def onEndOfSnapshot(self, itemName, itemPos):
    pass
  def onItemLostUpdates(self, itemName, itemPos, lostUpdates):
    pass
  def onListenEnd(self, subscription):
    pass
  def onListenStart(self, subscription):
    pass
  def onSubscription(self):
    pass
  def onSubscriptionError(self, code, message):
    pass
  def onUnsubscription(self):
    pass
  def onRealMaxFrequency(self, frequency):
    pass