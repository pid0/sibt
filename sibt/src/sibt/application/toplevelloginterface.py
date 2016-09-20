from sibt.infrastructure.filesdbschedulingslog import FilesDBSchedulingsLog
from sibt.application.configrepo import readRulesIntoFinder, isSysRule, \
    openLogs
from sibt.application.rulesfinder import EmptyRepo, RulesFinder

class _ThinRule(object):
  def __init__(self, name, enabled):
    self.name = name
    self.enabled = enabled

class _ThinRuleFactory(object):
  def readRule(self, name, ruleOptions, schedulerOptions, synchronizerOptions,
      isEnabled):
    return _ThinRule(name, isEnabled)

class TopLevelLogInterface(object):
  def __init__(self, paths, sysPaths):
    self.userLog, self.sysLog = openLogs(paths, sysPaths)

    self.rulesFinder = readRulesIntoFinder(paths, sysPaths, _ThinRuleFactory(),
        _ThinRuleFactory(), lambda rule: True,
        readUserConf=paths is not None,
        readSysConf=sysPaths is not None)

  def loggingsOfRules(self, *patterns):
    rules = self.rulesFinder.findRulesByPatterns(patterns, onlySyncRules=False, 
        keepUnloadedRules=True)

    userRuleNames = [rule.name for rule in rules if not isSysRule(rule)]
    sysRuleNames = [rule.name for rule in rules if isSysRule(rule)]

    ret = self.userLog.loggingsOfRules(userRuleNames)
    ret.update(self.sysLog.loggingsOfRules(sysRuleNames))
    return ret
