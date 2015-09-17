from fnmatch import fnmatchcase
from sibt.application.exceptions import RulePatternMismatchException

def _findRulePattern(pattern, enabledNames, disabledNames):
  if pattern in disabledNames or pattern in enabledNames:
    return [pattern]

  return [name for name in enabledNames if fnmatchcase(name, pattern)]

class RulesFinder(object):
  def __init__(self, configRepo):
    self.configRepo = configRepo

  def findRulesByPatterns(self, patterns, onlySyncRules, 
      keepUnloadedRules=False):
    rules = self.configRepo.userRules
    enabledNames = self.configRepo.userRules.enabledNames
    disabledNames = self.configRepo.userRules.disabledNames

    if not onlySyncRules:
      enabledNames += self.configRepo.userRules.names + \
          self.configRepo.sysRules.names
      disabledNames = []

    matchingNamesLists = [_findRulePattern(pattern, enabledNames, 
            disabledNames) for pattern in patterns]

    for matchingNames, pattern in zip(matchingNamesLists, patterns):
      if len(matchingNames) == 0:
        raise RulePatternMismatchException(pattern)

    return [self.findRuleByName(name, onlySyncRules, keepUnloadedRules) for 
        name in set(_flatten(matchingNamesLists))]

  def findRuleByName(self, name, onlySyncRules, keepUnloadedRule):
    if onlySyncRules:
      return self.configRepo.userRules.getRule(name, keepUnloadedRule)
    else:
      if name in self.configRepo.userRules.names:
        return self.configRepo.userRules.getRule(name, keepUnloadedRule)
      else:
        return self.configRepo.sysRules.getRule(name, keepUnloadedRule)

def _flatten(xss):
  return [x for xs in xss for x in xs]
