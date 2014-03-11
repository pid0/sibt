from sibt.domain.syncrule import SyncRule
from sibt.configuration.exceptions import ConfigConsistencyException

class RuleFactory(object):
  def __init__(self, schedulers, interpreters):
    self.schedulers = schedulers
    self.interpreters = interpreters

  def build(self, name, schedulerOptions, interpreterOptions, enabled):
    scheduler = self._findName(self.schedulers, schedulerOptions["Name"], 
        "scheduler")
    interpreter = self._findName(self.interpreters, interpreterOptions["Name"], 
        "interpreter")
    del schedulerOptions["Name"]
    del interpreterOptions["Name"]

    self._throwIfUnsupported(scheduler, schedulerOptions, "scheduler")
    self._throwIfUnsupported(interpreter, interpreterOptions, "interpreter")

    return SyncRule(name, schedulerOptions, interpreterOptions, enabled, 
        scheduler, interpreter)

  def _unsupportedOptions(self, configurable, options):
    supported = configurable.availableOptions
    return [key for key in options.keys() if key not in supported]

  def _throwIfUnsupported(self, configurable, options, description):
    unsupportedOptions = self._unsupportedOptions(configurable, options)
    if len(unsupportedOptions) > 0:
      raise ConfigConsistencyException("unsupported {0} options: {1}".format(
          description, unsupportedOptions))

  def _findName(self, objects, expectedName, searchDescription):
    matching = [obj for obj in objects if obj.name == expectedName]
    if len(matching) == 0:
      raise ConfigConsistencyException("{0} with name {1} not found".format(
          searchDescription, expectedName))
    return matching[0]
