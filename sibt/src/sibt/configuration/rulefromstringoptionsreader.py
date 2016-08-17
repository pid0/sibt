from sibt.configuration.exceptions import ConfigurableNotFoundException, \
    OptionParseException, ConfigConsistencyException
from sibt.domain import syncrule
from sibt.domain.synchronizeroptions import SynchronizerOptions

def makeException(ruleName, message):
  return ConfigConsistencyException("rule", ruleName, message)

class RuleFromStringOptionsReader(object):
  def __init__(self, ruleFactory, optionsParser, schedulers, synchronizers):
    self.ruleFactory = ruleFactory
    self.schedulers = schedulers
    self.synchronizers = synchronizers
    self.optionsParser = optionsParser

  def readRule(self, ruleName, ruleOptions, schedulerOptions, 
      synchronizerOptions, isEnabled):
    scheduler = self._findByNameOption(self.schedulers, schedulerOptions,
        "scheduler", ruleName)
    synchronizer = self._findByNameOption(self.synchronizers, 
        synchronizerOptions, "synchronizer", ruleName)

    parsedRuleOpts, parsedSchedOpts, parsedSyncerOpts = \
      self._collectingParseErrors(ruleName, 
          ("[Rule]", "[Scheduler]", "[Synchronizer]"),
          lambda: self._parseOptions(syncrule.AvailableOptions, ruleOptions, 
            False), 
          lambda: self._parseOptions(scheduler.availableOptions, 
            schedulerOptions, True), 
          lambda: SynchronizerOptions.fromDict(self._parseOptions(
            synchronizer.availableOptions, synchronizerOptions, True)))

    return self.ruleFactory.build(ruleName, scheduler, synchronizer,
        parsedRuleOpts, parsedSchedOpts, parsedSyncerOpts, isEnabled)

  def _findByNameOption(self, objects, options, searchDescription, ruleName):
    expectedName = self._getNameOrThrowEx(options, searchDescription, ruleName)
    matching = [obj for obj in objects if obj.name == expectedName]
    if len(matching) == 0:
      raise ConfigurableNotFoundException(searchDescription, expectedName,
          None, ruleName)
    return matching[0]

  def _getNameOrThrowEx(self, options, unitType, ruleName):
    if "Name" not in options:
      raise ConfigurableNotFoundException(unitType, None, 
          "Name option not given", ruleName)
    return options["Name"]

  def _parseOptions(self, optionInfos, options, removeNameOpt):
    if removeNameOpt:
      del options["Name"]

    return self.optionsParser.parseOptions(optionInfos, options)

  def _collectingParseErrors(self, ruleName, descriptions, *funcs):
    exceptions = []
    ret = []

    for func in funcs:
      try:
        ret.append(func())
        exceptions.append(None)
      except OptionParseException as ex:
        exceptions.append(ex)
    
    if any(ex is not None for ex in exceptions):
      raise makeException(ruleName, "\n".join(desc + " " + str(ex) for 
        desc, ex in zip(descriptions, exceptions) if ex is not None))
    return ret
