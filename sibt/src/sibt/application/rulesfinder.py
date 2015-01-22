from sibt.domain.rulescoordinator import RulesCoordinator
from fnmatch import fnmatchcase
from sibt.application.exceptions import RulePatternsMismatchException

def _findRulePattern(pattern, enabledNames, disabledNames):
  if pattern in disabledNames:
    return [pattern]

  return [name for name in enabledNames if fnmatchcase(name, pattern)]

class RulesFinder(object):
  def __init__(self, configRepo):
    self.configRepo = configRepo

  def findSyncRuleSetByPatterns(self, patterns):
    rules = self.configRepo.userRules
    enabledNames = self.configRepo.userRules.enabledNames
    disabledNames = self.configRepo.userRules.disabledNames
    matchingNames = _flatten([_findRulePattern(pattern, enabledNames, 
            disabledNames) for pattern in patterns])

    if len(matchingNames) == 0:
      raise RulePatternsMismatchException(patterns)
    return RulesCoordinator([self.configRepo.userRules.getRule(name) for name in
      matchingNames])

  def findRuleByName(self, name, onlySyncRules):
    if onlySyncRules:
      return self.configRepo.userRules.getRule(name)
    else:
      if name in self.configRepo.userRules.names:
        return self.configRepo.userRules.getRule(name)
      else:
        return self.configRepo.sysRules.getRule(name)

def _flatten(xss):
  return [x for xs in xss for x in xs]
