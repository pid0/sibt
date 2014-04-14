from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.domain.queuingscheduler import QueuingScheduler
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException
from sibt.infrastructure import collectFilesInDirs
import sys
from sibt.domain.rulefactory import RuleFactory
from fnmatch import fnmatchcase
import itertools
from sibt.application.runner import Runner
from sibt.application.hashbangawareprocessrunner import \
    HashbangAwareProcessRunner

def readInterpreters(dirs, processRunner):
  def load(path, fileName):
    try:
      return ExecutableFileRuleInterpreter.createWithFile(path, fileName, 
        processRunner)
    except ConfigConsistencyException:
      return None

  return collectFilesInDirs(dirs, load)

def readSchedulers(dirs, loader, initArgs):
  return collectFilesInDirs(dirs, lambda path, fileName:
      QueuingScheduler(loader.loadFromFile(path, fileName, initArgs)))

def readRules(rulesDir, enabledDir, factory):
  reader = DirBasedRulesReader(rulesDir, enabledDir, factory)
  return list(reader.read())

def findRulePattern(pattern, enabledRules, disabledRules):
  matchingDisabled = [rule for rule in disabledRules if rule.name == pattern]
  if len(matchingDisabled) == 1:
    return matchingDisabled

  return [rule for rule in enabledRules if fnmatchcase(rule.name, pattern)]

def createHashbangAwareProcessRunner(runnersDir, processRunner):
  runners = collectFilesInDirs([runnersDir], 
      lambda path, fileName: Runner(fileName, path))
  return HashbangAwareProcessRunner(runners, processRunner)
  

class ConfigRepo(object):
  def __init__(self, schedulers, interpreters, rules, sysRules):
    self.schedulers = schedulers
    self.interpreters = interpreters
    self.rules = rules
    self.sysRules = sysRules

  @classmethod
  def load(clazz, paths, sysPaths, readSysConf, processRunner, 
      schedulerLoader, sibtInvocation):
    processRunnerWrapper = createHashbangAwareProcessRunner(paths.runnersDir,
        processRunner)

    interpreters = readInterpreters([paths.interpretersDir, 
      paths.readonlyInterpretersDir] + ([sysPaths.interpretersDir] if 
        readSysConf else []), processRunnerWrapper)
    schedulers = readSchedulers([paths.schedulersDir, 
      paths.readonlySchedulersDir] + ([sysPaths.schedulersDir] if 
        readSysConf else []), schedulerLoader, (sibtInvocation, paths))

    factory = RuleFactory(schedulers, interpreters)
    rules = readRules(paths.rulesDir, paths.enabledDir, factory)
    sysRules = [] if not readSysConf else readRules(sysPaths.rulesDir, 
        sysPaths.enabledDir, factory)

    return clazz(schedulers, interpreters, rules, sysRules)

  def allRules(self):
    return itertools.chain(self.rules, self.sysRules)
  allRules = property(allRules)

  def findSyncRulesByPatterns(self, patterns):
    rules = self.rules
    enabledRules = [rule for rule in rules if rule.enabled]
    disabledRules = [rule for rule in rules if not rule.enabled]
    ruleLists = [findRulePattern(pattern, enabledRules, 
            disabledRules) for pattern in patterns]
    return [rule for ruleList in ruleLists for rule in ruleList]
