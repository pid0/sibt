from sibt.domain.scheduling import Scheduling
from sibt.domain.version import Version
from sibt.domain.exceptions import UnsupportedProtocolException
from sibt.infrastructure.types import Enum
from sibt.domain.optioninfo import OptionInfo

LocCheckLevel = Enum("None", "Default", "Strict")

AvailableOptions = [OptionInfo("LocCheckLevel", LocCheckLevel)]

class SyncRule(object):
  def __init__(self, name, options, schedulerOptions, synchronizerOptions, 
      enabled, scheduler, synchronizer):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.synchronizer = synchronizer
    self.ports = synchronizer.ports
    self.options = options
    self._onePortMustHaveFileProtocol = synchronizer.onePortMustHaveFileProtocol

    self.locs = synchronizerOptions.locs

    for i, (loc, port) in enumerate(zip(self.locs, self.ports)):
      self._throwIfPortCantUseLoc(port, loc, "Loc" + str(i + 1))

    if self._onePortMustHaveFileProtocol:
      self._throwIfNotAtLeastOneIsLocal(self.locs, synchronizerOptions.locKeys)

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
    locIndex = locNumber - 1
    if self._onePortMustHaveFileProtocol:
      self._throwIfNotAtLeastOneIsLocal(self.locs[:locIndex] + 
          [destinationLocation] + self.locs[locIndex+1:], ["restore target"])

    self._throwIfPortCantUseLoc(self.ports[locIndex], destinationLocation,
        "restore target")

    self.synchronizer.restore(self._loc(locNumber).relativePathTo(location), 
        locNumber, version.time, destinationLocation, 
        self.synchronizerOptions)

  def listFiles(self, location, version, recursively):
    locNumber = self._getLocNumber(location)
    return self.synchronizer.listFiles(
        self._loc(locNumber).relativePathTo(location), 
        locNumber, version.time, recursively, self.synchronizerOptions)

  def _getLocNumber(self, path):
    for i, loc in enumerate(self.locs):
      if loc.contains(path):
        return i + 1
    return None

  def _throwIfNotAtLeastOneIsLocal(self, locations, affectedOptions):
    if all(loc.protocol != "file" for loc in locations):
      raise UnsupportedProtocolException(self.name, "/".join(affectedOptions),
          "a remote", explanation="at least one location must be a local path")

  def _throwIfPortCantUseLoc(self, port, loc, optionName):
    if not port.canBeAssignedLocation(loc):
      raise UnsupportedProtocolException(self.name, optionName,
          loc.protocol, port.supportedProtocols)

  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.synchronizerOptions, self.enabled, self.scheduler, 
      self.synchronizer))

  def __eq__(self, other):
    return self.name == other.name
  def __hash__(self):
    return hash(self.name)
