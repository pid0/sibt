from sibt.domain.scheduling import Scheduling
from sibt.infrastructure.pathhelper import removeCommonPrefix, isPathWithinPath
from sibt.domain.version import Version

LocKeys = ["Loc1", "Loc2"]

class SyncRule(object):
  def __init__(self, name, schedulerOptions, interpreterOptions, enabled, 
      scheduler, interpreter):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.interpreter = interpreter

    self.locs = [interpreterOptions[key] for key in LocKeys]
    self.interpreterOptions = interpreterOptions

    writeLocIndices = list(interpreter.writeLocIndices)
    self.writeLocs = [self._loc(i) for i in writeLocIndices]
    self.nonWriteLocs = [self._loc(i) for i in range(1, 3) if i not in 
        writeLocIndices]

  def _loc(self, index):
    return self.locs[index - 1]

  @property
  def scheduling(self):
    return Scheduling(self.name, self.schedulerOptions)

  def sync(self):
    self.interpreter.sync(self.interpreterOptions)

  def versionsOf(self, location):
    locNumber = self._getLocNumber(location)
    if locNumber is None:
      return []
    return [Version(self, time) for time in 
        self.interpreter.versionsOf(
            removeCommonPrefix(str(location), str(self._loc(locNumber))), 
            locNumber, self.interpreterOptions)]

  def restore(self, location, version, destinationLocation):
    locNumber = self._getLocNumber(location)
    self.interpreter.restore(removeCommonPrefix(
      str(location), str(self._loc(locNumber))),
        locNumber, version.time, str(destinationLocation), 
        self.interpreterOptions)

  def listFiles(self, location, version, recursively):
    locNumber = self._getLocNumber(location)
    return self.interpreter.listFiles(
        removeCommonPrefix(str(location), str(self._loc(locNumber))),
        locNumber, version.time, recursively, self.interpreterOptions)

  def _getLocNumber(self, path):
    return 1 if isPathWithinPath(str(path), str(self._loc(1))) else 2 if \
        isPathWithinPath(str(path), str(self._loc(2))) else None

  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.interpreterOptions, self.enabled, self.scheduler, 
      self.interpreter))

  def __eq__(self, other):
    return self.name == other.name
  def __hash__(self):
    return hash(self.name)
