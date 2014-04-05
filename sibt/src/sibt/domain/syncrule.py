from sibt.domain.scheduling import Scheduling
from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode

class SyncRule(object):
  def __init__(self, name, schedulerOptions, interpeterOptions, enabled, 
      scheduler, interpreter):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.interpreterOptions = interpeterOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.interpreter = interpreter

  def _scheduling(self):
    return Scheduling(self.name, self.schedulerOptions)

  def schedule(self):
    self.scheduler.run([self._scheduling()])
  def sync(self):
    self.interpreter.sync(self.interpreterOptions)

  def checkScheduler(self):
    return ["in {0}: {1}".format(self.name, error) for error in
        self.scheduler.check(self._scheduling())]

  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.interpreterOptions, self.enabled, self.scheduler, self.interpreter))
