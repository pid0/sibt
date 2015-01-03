from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.domain.defaultvalueinterpreter import DefaultValueInterpreter
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
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader

def readInterpreters(dirs, processRunner):
  def load(path, fileName):
    try:
      return DefaultValueInterpreter(ExecutableFileRuleInterpreter.
          createWithFile(path, fileName, processRunner))
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
  def __init__(self, schedulers, interpreters, userRules, sysRules):
    self.schedulers = schedulers
    self.interpreters = interpreters
    self.userRules = userRules
    self.sysRules = sysRules

  @classmethod
  def load(clazz, paths, sysPaths, readSysConf, processRunner, 
      moduleLoader, sibtInvocation):
    processRunnerWrapper = createHashbangAwareProcessRunner(paths.runnersDir,
        processRunner)

    interpreters = readInterpreters([paths.interpretersDir, 
      paths.readonlyInterpretersDir] + ([sysPaths.interpretersDir] if 
        readSysConf else []), processRunnerWrapper)
    schedulers = readSchedulers(
        [paths.schedulersDir, paths.readonlySchedulersDir] + 
        ([sysPaths.schedulersDir] if readSysConf else []), 
        PyModuleSchedulerLoader(moduleLoader), (sibtInvocation, paths))

    factory = RuleFactory(schedulers, interpreters)
    userRules = readRules(paths.rulesDir, paths.enabledDir, factory)
    sysRules = [] if not readSysConf else readRules(sysPaths.rulesDir, 
        sysPaths.enabledDir, factory)

    return clazz(schedulers, interpreters, userRules, sysRules)

  @property
  def allRules(self):
    return itertools.chain(self.userRules, self.sysRules)

  def findSyncRulesByPatterns(self, patterns):
    rules = self.userRules
    enabledRules = [rule for rule in rules if rule.enabled]
    disabledRules = [rule for rule in rules if not rule.enabled]
    ruleLists = [findRulePattern(pattern, enabledRules, 
            disabledRules) for pattern in patterns]
    return [rule for ruleList in ruleLists for rule in ruleList]

  def findSyncRuleByName(self, name):
    matching = [rule for rule in self.userRules if rule.name == name]
    if len(matching) == 0:
      return None
    return matching[0]
