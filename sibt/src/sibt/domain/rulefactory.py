from sibt.domain.syncrule import SyncRule
from sibt.configuration.exceptions import ConfigConsistencyException

def makeException(ruleName, message):
  return ConfigConsistencyException("rule", ruleName, message)

class RuleFactory(object):
  def __init__(self, schedulers, interpreters):
    self.schedulers = schedulers
    self.interpreters = interpreters

  def build(self, name, schedulerOptions, interpreterOptions, enabled):
    self._throwIfOptionsNotPresent(schedulerOptions, ["Name"], "scheduler", 
        name)
    self._throwIfOptionsNotPresent(interpreterOptions, 
        ["Name", "Loc1", "Loc2"], "interpreter (Loc1, Loc2, Name)", name)

    scheduler = self._findName(self.schedulers, schedulerOptions["Name"], 
        "scheduler", name)
    interpreter = self._findName(self.interpreters, interpreterOptions["Name"], 
        "interpreter", name)
    del schedulerOptions["Name"]
    del interpreterOptions["Name"]

    self._throwIfUnsupported(scheduler, schedulerOptions, [], "scheduler", name)
    self._throwIfUnsupported(interpreter, interpreterOptions, 
        ["Loc1", "Loc2"], "interpreter", name)

    return SyncRule(name, schedulerOptions, interpreterOptions, enabled, 
        scheduler, interpreter)

  def _throwIfOptionsNotPresent(self, options, expectedOptions, 
      minimumOptsDescription, ruleName):
    if not all(option in options for option in expectedOptions):
      raise makeException(ruleName, "does not have minimum options for {0}".
          format(minimumOptsDescription))
  def _schedulerMinimumMet(self, interpreter, options):
    return "Name" in options
  def _interpreterMinimumMet(self, interpreter, options):
    return "Name" in options and "Loc1" in options and "Loc2" in options

  def _unsupportedOptions(self, configurable, options, predefinedOptions):
    supported = configurable.availableOptions + predefinedOptions
    return [key for key in options.keys() if key not in supported]

  def _throwIfUnsupported(self, configurable, options, predefinedOptions, 
      description, ruleName):
    unsupportedOptions = self._unsupportedOptions(configurable, options, 
        predefinedOptions)
    if len(unsupportedOptions) > 0:
      raise makeException(ruleName, "unsupported {0} options: {1}".format(
          description, ", ".join(unsupportedOptions)))

  def _findName(self, objects, expectedName, searchDescription, ruleName):
    matching = [obj for obj in objects if obj.name == expectedName]
    if len(matching) == 0:
      raise makeException(ruleName, "{0} with name ‘{1}’ not found".format(
          searchDescription, expectedName))
    return matching[0]
