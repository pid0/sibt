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

    writeLocIndices = list(interpreter.writeLocIndices)
    self.writeLocs = [self._loc(i) for i in writeLocIndices]
    self.nonWriteLocs = [self._loc(i) for i in range(1, 3) if i not in 
        writeLocIndices]

  @property
  def locs(self):
    yield self._loc(1)
    yield self._loc(2)

  def _loc(self, index):
    return self.interpreterOptions["Loc" + str(index)]

  @property
  def scheduling(self):
    return Scheduling(self.name, self.schedulerOptions)

  def sync(self):
    self.interpreter.sync(self.interpreterOptions)

  def versionsOf(self, path):
    locNumber = self._getLocNumber(path)
    if locNumber is None:
      return []
    return [Version(self, time) for time in 
        self.interpreter.versionsOf(
            removeCommonPrefix(path, self._loc(locNumber)), locNumber,
            self.interpreterOptions)]

  def restore(self, path, version, destination):
    locNumber = self._getLocNumber(path)
    self.interpreter.restore(removeCommonPrefix(path, self._loc(locNumber)),
        locNumber, version.time, destination, self.interpreterOptions)

  def listFiles(self, path, version, recursively):
    locNumber = self._getLocNumber(path)
    return self.interpreter.listFiles(
        removeCommonPrefix(path, self._loc(locNumber)),
        locNumber, version.time, recursively, self.interpreterOptions)

  def _getLocNumber(self, path):
    return 1 if isPathWithinPath(path, self._loc(1)) else 2 if \
        isPathWithinPath(path, self._loc(2)) else None

  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.interpreterOptions, self.enabled, self.scheduler, self.interpreter))

  def __eq__(self, other):
    return self.name == other.name
  def __hash__(self):
    return hash(self.name)
