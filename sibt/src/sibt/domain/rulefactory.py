from sibt.domain.syncrule import SyncRule
from sibt.domain.exceptions import LocationInvalidException
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.configuration.optionvaluesparser import parseLocation

def makeException(ruleName, message):
  return ConfigConsistencyException("rule", ruleName, message)

class RuleFactory(object):
  def __init__(self, schedulers, synchronizers):
    self.schedulers = schedulers
    self.synchronizers = synchronizers

  def build(self, name, schedulerOptions, synchronizerOptions, enabled):
    self._throwIfOptionsNotPresent(schedulerOptions, ["Name"], "scheduler", 
        name)
    self._throwIfOptionsNotPresent(synchronizerOptions, 
        ["Name"], "synchronizer", name)

    scheduler = self._findName(self.schedulers, schedulerOptions["Name"], 
        "scheduler", name)
    synchronizer = self._findName(self.synchronizers, 
        synchronizerOptions["Name"], "synchronizer", name)
    del schedulerOptions["Name"]
    del synchronizerOptions["Name"]

    locOptions = self._locOptionsCorrespondingToPorts(synchronizer.ports)
    self._throwIfOptionsNotPresent(synchronizerOptions, locOptions, 
        "synchronizer", name)

    self._throwIfUnsupported(scheduler, schedulerOptions, [], "scheduler", name)
    self._throwIfUnsupported(synchronizer, synchronizerOptions, 
        locOptions, "synchronizer", name)

    return SyncRule(name, schedulerOptions, 
        self._wrapLocs(name, locOptions, synchronizerOptions), 
        enabled, scheduler, synchronizer)

  def _throwIfOptionsNotPresent(self, options, expectedOptions, 
      unitName, ruleName):
    if not all(option in options for option in expectedOptions):
      raise makeException(ruleName, 
          "does not have minimum options for {0} ({1})".format(
            unitName, ",".join(expectedOptions)))

  def _locOptionsCorrespondingToPorts(self, ports):
    return ["Loc" + str(i + 1) for i in range(len(ports))]

  def _wrapLocs(self, ruleName, locOptionNames, syncerOpts):
    ret = dict(syncerOpts)
    try:
      for loc in locOptionNames:
        ret[loc] = parseLocation(ret[loc])
    except LocationInvalidException as ex:
      raise makeException(ruleName, str(ex))
    return ret

  def _throwIfUnsupported(self, configurable, options, predefinedOptions, 
      description, ruleName):
    unsupportedOptions = self._unsupportedOptions(configurable, options, 
        predefinedOptions)
    if len(unsupportedOptions) > 0:
      raise makeException(ruleName, "unsupported {0} options: {1}".format(
          description, ", ".join(unsupportedOptions)))

  def _unsupportedOptions(self, configurable, options, predefinedOptions):
    supported = configurable.availableOptions + predefinedOptions
    return [key for key in options.keys() if key not in supported]

  def _findName(self, objects, expectedName, searchDescription, ruleName):
    matching = [obj for obj in objects if obj.name == expectedName]
    if len(matching) == 0:
      raise makeException(ruleName, "{0} with name ‘{1}’ not found".format(
          searchDescription, expectedName))
    return matching[0]
