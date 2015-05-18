from sibt.domain.syncrule import SyncRule
from sibt.domain import syncrule
from sibt.domain.exceptions import LocationInvalidException
from sibt.configuration.exceptions import ConfigConsistencyException, \
    RuleNameInvalidException
from sibt.configuration.optionvaluesparser import parseLocation
from sibt.domain.syncrule import LocCheckLevel
from sibt.domain.optioninfo import OptionInfo

def makeException(ruleName, message):
  return ConfigConsistencyException("rule", ruleName, message)

class RuleFactory(object):
  def build(self, name, scheduler, synchronizer, ruleOptions, 
      schedulerOptions, synchronizerOptions, enabled):
    self._throwIfRuleNameInvalid(name)

    self._throwIfLocOptionsNotPresent(synchronizerOptions, synchronizer.ports, 
        name)

    self._throwIfUnsupported(scheduler.availableOptions, 
        schedulerOptions, "scheduler", name)
    self._throwIfUnsupported(synchronizer.availableOptions,
        synchronizerOptions, "synchronizer", name)
    self._throwIfUnsupported(syncrule.AvailableOptions, ruleOptions, "rule", 
        name)

    self._setRuleOptionsDefaultValues(ruleOptions)

    return SyncRule(name, ruleOptions, schedulerOptions, synchronizerOptions,
        enabled, scheduler, synchronizer)

  def _throwIfLocOptionsNotPresent(self, syncerOpts, ports, ruleName):
    diff = len(ports) - len(syncerOpts.locs)
    if diff > 0:
      raise makeException(ruleName, 
          "does not have minimum options for synchronizer ({0})".format(
            ",".join("Loc" + str(i + 1) for i in range(len(syncerOpts.locs),
              len(ports)))))

  def _throwIfRuleNameInvalid(self, name):
    if "," in name:
      raise RuleNameInvalidException(name, ",")
    if " " in name:
      raise RuleNameInvalidException(name, " ")

  def _throwIfUnsupported(self, supportedOptionInfos, options, description, 
      ruleName):
    unsupportedOptions = self._unsupportedOptions(supportedOptionInfos, options)
    if len(unsupportedOptions) > 0:
      raise makeException(ruleName, "unsupported {0} options: {1}".format(
          description, ", ".join(unsupportedOptions)))

  def _unsupportedOptions(self, supportedOptionInfos, options):
    supportedNames = [opt.name for opt in supportedOptionInfos]
    return [key for key in options.keys() if key not in supportedNames]

  def _setRuleOptionsDefaultValues(self, options):
    if "LocCheckLevel" not in options:
      options["LocCheckLevel"] = LocCheckLevel.Default
    else:
      for possibleOption in LocCheckLevel.values:
        if options["LocCheckLevel"] == possibleOption.name:
          options["LocCheckLevel"] = possibleOption
