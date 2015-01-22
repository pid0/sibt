from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.domain.defaultvalueinterpreter import DefaultValueInterpreter
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException
from sibt.infrastructure import collectFilesInDirs
import sys
from sibt.domain.rulefactory import RuleFactory
import itertools
from sibt.application.runner import Runner
from sibt.application.hashbangawareprocessrunner import \
    HashbangAwareProcessRunner
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.application.exceptions import RuleNameMismatchException

def readInterpreters(dirs, processRunner):
  def load(path, fileName):
    try:
      return DefaultValueInterpreter(ExecutableFileRuleInterpreter.
          createWithFile(path, fileName, processRunner))
    except ConfigConsistencyException:
      return None

  return collectFilesInDirs(dirs, load)

def readSchedulers(dirs, loader, schedulerWrapper, initArgs):
  return collectFilesInDirs(dirs, lambda path, fileName:
      schedulerWrapper(loader.loadFromFile(path, fileName, initArgs)))

def readRules(rulesDir, enabledDir, factory, prefix):
  reader = DirBasedRulesReader(rulesDir, enabledDir, factory, prefix)
  return list(reader.read())

def createHashbangAwareProcessRunner(runnersDir, processRunner):
  runners = collectFilesInDirs([runnersDir], 
      lambda path, fileName: Runner(fileName, path))
  return HashbangAwareProcessRunner(runners, processRunner)
  

class ConfigRepo(object):
  def __init__(self, schedulers, interpreters, userRules, sysRules):
    self.schedulers = schedulers
    self.interpreters = interpreters
    self.userRules = RulesRepo(userRules)
    self.sysRules = RulesRepo(sysRules)

  @classmethod
  def load(clazz, paths, sysPaths, readSysConf, processRunner, 
      moduleLoader, sibtInvocation, schedulerWrapper):
    processRunnerWrapper = createHashbangAwareProcessRunner(paths.runnersDir,
        processRunner)

    interpreters = readInterpreters([paths.interpretersDir, 
      paths.readonlyInterpretersDir] + ([sysPaths.interpretersDir] if 
        readSysConf else []), processRunnerWrapper)
    schedulers = readSchedulers(
        [paths.schedulersDir, paths.readonlySchedulersDir] + 
        ([sysPaths.schedulersDir] if readSysConf else []), 
        PyModuleSchedulerLoader(moduleLoader), schedulerWrapper,
        (sibtInvocation, paths))

    factory = RuleFactory(schedulers, interpreters)
    userRules = readRules(paths.rulesDir, paths.enabledDir, factory, "")
    sysRules = [] if not readSysConf else readRules(sysPaths.rulesDir, 
        sysPaths.enabledDir, factory, "+")

    return clazz(schedulers, interpreters, userRules, sysRules)

  def getAllRules(self):
    return itertools.chain(self.userRules.getAll(), self.sysRules.getAll())

class RulesRepo(object):
  def __init__(self, rules):
    self._namesToRules = dict((rule.name, rule) for rule in rules)
    self.names = list(self._namesToRules.keys())
    self.enabledNames = [rule.name for rule in rules if rule.enabled]
    self.disabledNames = [rule.name for rule in rules if not rule.enabled]
  
  def getRule(self, name):
    try:
      return self._namesToRules[name]
    except KeyError:
      raise RuleNameMismatchException(name)
  
  def getAll(self):
    return self._namesToRules.values()
