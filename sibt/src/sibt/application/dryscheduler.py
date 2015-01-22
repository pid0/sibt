class DryScheduler(object):
  def __init__(self, subScheduler, output):
    self.subScheduler = subScheduler
    self.output = output

  def __getattr__(self, name):
    return getattr(self.subScheduler, name)

  def run(self, schedulings):
    for scheduling in schedulings:
      self.output.println("scheduling ‘{0}’ with ‘{1}’".format(
        scheduling.ruleName, self.subScheduler.name))

