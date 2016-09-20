from sibt.domain.scheduling import Scheduling
from sibt.domain.version import Version
from sibt.domain.exceptions import UnsupportedProtocolException, \
    UnstablePhaseException, ValidationException
from sibt.infrastructure.types import Enum
from sibt.domain.optioninfo import OptionInfo
from sibt.infrastructure import types
from sibt.domain.schedulinglogging import SchedulingLogging, SchedulingResult
from sibt.domain.ruleset import RuleSet

LocCheckLevel = Enum("None", "Default", "Strict")

AvailableOptions = [
    OptionInfo("LocCheckLevel", LocCheckLevel),
    OptionInfo("AllowedForUsers", types.String)]

class SyncRule(object):
  def __init__(self, name, options, schedulerOptions, synchronizerOptions, 
      enabled, scheduler, synchronizer, log):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.synchronizer = synchronizer
    self.log = log
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
    self.syncerName = synchronizer.name

  def _loc(self, index):
    return self.locs[index - 1]

  @property
  def scheduling(self):
    return Scheduling(self.name, self.schedulerOptions)

  @property
  def latestExecution(self):
    executions = self.log.loggingsOfRules([self.name])[self.name]
    if len(executions) == 0:
      return None
    return executions[-1]

  @property
  def executing(self):
    lastExecution = self.latestExecution
    try:
      return not lastExecution.finished
    except AttributeError:
      return False

  @property
  def nextExecution(self):
    if self.executing:
      return None
    try:
      lastExecutionTime = self.latestExecution.endTime
    except AttributeError:
      lastExecutionTime = None

    nextExecutionTime = self.scheduler.nextExecutionTime(self.scheduling, 
        lastExecutionTime)
    if nextExecutionTime is None:
      return None
    return SchedulingLogging(nextExecutionTime, b"", None)

  def sync(self, validator, mutexManager):
    validationErrors = validator.validate(RuleSet([self]))
    if len(validationErrors) > 0:
      raise ValidationException(validationErrors)

    with mutexManager.lockForId(self.name):
      self.synchronizer.sync(self.synchronizerOptions)

  def versionsOf(self, location, unstablePhaseDetector):
    locNumber = self._getLocNumber(location)
    if locNumber is None:
      return []
    if unstablePhaseDetector.isInUnstablePhase(self):
      raise UnstablePhaseException()

    return [Version(self, time) for time in 
        self.synchronizer.versionsOf(
          self._loc(locNumber).relativePathTo(location), 
          locNumber, self.synchronizerOptions)]

  def restore(self, location, version, destinationLocation, 
      unstablePhaseDetector):
    if unstablePhaseDetector.isInUnstablePhase(self):
      raise UnstablePhaseException()

    locNumber = self._getLocNumber(location)
    locIndex = locNumber - 1

    if destinationLocation is not None:
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

  @property
  def syncerCheckErrors(self):
    return self.synchronizer.check(self.synchronizerOptions)

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
