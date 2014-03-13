class QueuingScheduler(object):
  def __init__(self, subScheduler):
    self.subScheduler = subScheduler
    self.queue = []

  def __getattr__(self, name):
    return getattr(self.subScheduler, name)

  def run(self, schedulings):
    self.queue += schedulings

  def executeSchedulings(self):
    if len(self.queue) == 0:
      return
    self.subScheduler.run(self.queue)
