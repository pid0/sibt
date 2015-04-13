from sibt.domain.scheduling import Scheduling
from sibt.domain.version import Version
from sibt.domain.exceptions import UnsupportedProtocolException

class SyncRule(object):
  def __init__(self, name, schedulerOptions, synchronizerOptions, enabled, 
      scheduler, synchronizer):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.synchronizer = synchronizer
    self.ports = synchronizer.ports

    locKeys = ["Loc" + str(i + 1) for i in range(len(self.ports))]
    self.locs = [synchronizerOptions[key] for key in locKeys]

    for i in range(len(self.locs)):
      if not self.ports[i].canBeAssignedLocation(self.locs[i]):
        raise UnsupportedProtocolException(name,
            "Loc" + str(i + 1), self.locs[i].protocol,
            self.ports[i].supportedProtocols)

    self.writeLocs = [loc for loc, port in zip(self.locs, self.ports) if \
        port.isWrittenTo]
    self.nonWriteLocs = [loc for loc, port in zip(self.locs, self.ports) if \
        not port.isWrittenTo]

    self.synchronizerOptions = synchronizerOptions

  def _loc(self, index):
    return self.locs[index - 1]

  @property
  def scheduling(self):
    return Scheduling(self.name, self.schedulerOptions)

  def sync(self):
    self.synchronizer.sync(self.synchronizerOptions)

  def versionsOf(self, location):
    locNumber = self._getLocNumber(location)
    if locNumber is None:
      return []
    return [Version(self, time) for time in 
        self.synchronizer.versionsOf(
          self._loc(locNumber).relativePathTo(location), 
          locNumber, self.synchronizerOptions)]

  def restore(self, location, version, destinationLocation):
    locNumber = self._getLocNumber(location)
    self.synchronizer.restore(self._loc(locNumber).relativePathTo(location), 
        locNumber, version.time, str(destinationLocation), 
        self.synchronizerOptions)

  def listFiles(self, location, version, recursively):
    locNumber = self._getLocNumber(location)
    return self.synchronizer.listFiles(
        self._loc(locNumber).relativePathTo(location), 
        locNumber, version.time, recursively, self.synchronizerOptions)

  def _getLocNumber(self, path):
    for i in range(1, len(self.ports) + 1):
      if self._loc(i).contains(path):
        return i
    return None

  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.synchronizerOptions, self.enabled, self.scheduler, 
      self.synchronizer))

  def __eq__(self, other):
    return self.name == other.name
  def __hash__(self):
    return hash(self.name)
