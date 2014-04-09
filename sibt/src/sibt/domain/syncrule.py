from sibt.domain.scheduling import Scheduling
from sibt.infrastructure.pathhelper import removeCommonPrefix, isPathWithinPath
from sibt.domain.version import Version

class SyncRule(object):
  def __init__(self, name, schedulerOptions, interpeterOptions, enabled, 
      scheduler, interpreter):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.interpreterOptions = interpeterOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.interpreter = interpreter

  def _loc(self, index):
    return self.interpreterOptions["Loc" + str(index)]

  def _scheduling(self):
    return Scheduling(self.name, self.schedulerOptions)

  def schedule(self):
    self.scheduler.run([self._scheduling()])
  def sync(self):
    self.interpreter.sync(self.interpreterOptions)

  def checkScheduler(self):
    return self.scheduler.check([self._scheduling()])

  def versionsOf(self, path):
    locNumber = 1 if isPathWithinPath(path, self._loc(1)) else 2 if \
        isPathWithinPath(path, self._loc(2)) else 0
    if locNumber == 0:
      return []
    return [Version(self.name, time) for time in 
        self.interpreter.versionsOf(
            removeCommonPrefix(path, self._loc(locNumber)), locNumber,
            self.interpreterOptions)]

  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.interpreterOptions, self.enabled, self.scheduler, self.interpreter))
