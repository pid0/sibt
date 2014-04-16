class QueuingScheduler(object):
  def __init__(self, subScheduler):
    self.subScheduler = subScheduler
    self.runQueue = []
    self.checkQueue = []

  def __getattr__(self, name):
    return getattr(self.subScheduler, name)

  def run(self, schedulings):
    self.runQueue += schedulings
  def check(self, schedulings):
    self.checkQueue += schedulings

  def checkAll(self):
    return self.subScheduler.check(self.checkQueue)

  def executeSchedulings(self):
    if len(self.runQueue) == 0:
      return
    self.subScheduler.run(self.runQueue)
