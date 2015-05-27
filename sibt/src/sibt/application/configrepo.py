from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.configuration.cachinginifilesetreader import CachingIniFileSetReader
from sibt.configuration import dirbasedrulesreader
from sibt.domain.defaultvaluesynchronizer import DefaultValueSynchronizer
from sibt.infrastructure.functionmodulesynchronizer import \
    FunctionModuleSynchronizer
from sibt.configuration.exceptions import MissingConfigValuesException, \
    ConfigConsistencyException
from sibt.infrastructure import collectFilesInDirs
import sys
from sibt.configuration.rulefromstringoptionsreader import \
    RuleFromStringOptionsReader
from sibt.domain.rulefactory import RuleFactory
import itertools
from sibt.application.runner import Runner
from sibt.application.hashbangawareprocessrunner import \
    HashbangAwareProcessRunner
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.application.exceptions import RuleNameMismatchException
from sibt.infrastructure.runnablefilefunctionmodule import \
    RunnableFileFunctionModule
from sibt.configuration.optionvaluesparser import OptionValuesParser

def readSynchronizers(dirs, processRunner):
  def load(path, fileName):
    try:
      return loadSynchronizer(processRunner, path, fileName)
    except ConfigConsistencyException:
      return None

  return collectFilesInDirs(dirs, load)

def loadSynchronizer(processRunner, executablePath, name):
  functionModule = RunnableFileFunctionModule(processRunner, executablePath)
  return DefaultValueSynchronizer(FunctionModuleSynchronizer(functionModule,
    name))

def readSchedulers(dirs, loader, schedulerWrapper, initArgs):
  return collectFilesInDirs(dirs, lambda path, fileName:
      schedulerWrapper(loader.loadFromFile(path, fileName, initArgs)))

def readRuleLoaders(rulesDir, enabledDir, factory, prefix):
  reader = DirBasedRulesReader(CachingIniFileSetReader(rulesDir,
    dirbasedrulesreader.AllowedSections), 
      rulesDir, enabledDir, factory, prefix)
  return list(reader.read())

def createHashbangAwareProcessRunner(runnersDir, processRunner):
  runners = collectFilesInDirs([runnersDir], 
      lambda path, fileName: Runner(fileName, path))
  return HashbangAwareProcessRunner(runners, processRunner)
  

class ConfigRepo(object):
  def __init__(self, schedulers, synchronizers, lazyUserRules, lazySysRules):
    self.schedulers = schedulers
    self.synchronizers = synchronizers
    self.userRules = RulesRepo(lazyUserRules)
    self.sysRules = RulesRepo(lazySysRules)

  @classmethod
  def load(clazz, paths, sysPaths, readSysConf, processRunner, 
      moduleLoader, sibtInvocation, schedulerWrapper):
    processRunnerWrapper = createHashbangAwareProcessRunner(paths.runnersDir,
        processRunner)

    synchronizers = readSynchronizers([paths.synchronizersDir, 
      paths.readonlySynchronizersDir] + ([sysPaths.synchronizersDir] if 
        readSysConf else []), processRunnerWrapper)
    schedulers = readSchedulers(
        [paths.schedulersDir, paths.readonlySchedulersDir] + 
        ([sysPaths.schedulersDir] if readSysConf else []), 
        PyModuleSchedulerLoader(moduleLoader), schedulerWrapper,
        (sibtInvocation, paths))

    factory = RuleFromStringOptionsReader(RuleFactory(),
        OptionValuesParser(), schedulers, synchronizers)
    userRules = readRuleLoaders(paths.rulesDir, paths.enabledDir, factory, "")
    sysRules = [] if not readSysConf else readRuleLoaders(sysPaths.rulesDir, 
        sysPaths.enabledDir, factory, "+")

    return clazz(schedulers, synchronizers, userRules, sysRules)

  def getAllRules(self, keepUnloadedRules=False):
    return itertools.chain(self.userRules.getAll(keepUnloadedRules), 
        self.sysRules.getAll(keepUnloadedRules))

class RulesRepo(object):
  def __init__(self, lazyRules):
    self._namesToRules = dict((rule.name, rule) for rule in lazyRules)
    self._ruleRead = dict((rule.name, False) for rule in lazyRules)
    self.names = list(self._namesToRules.keys())
    self.enabledNames = [rule.name for rule in lazyRules if rule.enabled]
    self.disabledNames = [rule.name for rule in lazyRules if not rule.enabled]
  
  def getRule(self, name, keepUnloaded):
    try:
      if not self._ruleRead[name]:
        try:
          self._namesToRules[name] = self._namesToRules[name].load()
          self._ruleRead[name] = True
        except MissingConfigValuesException:
          if self._namesToRules[name].enabled or not keepUnloaded:
            raise
      return self._namesToRules[name]
    except KeyError:
      raise RuleNameMismatchException(name)
  
  def getAll(self, keepUnloadedRules):
    return [self.getRule(name, keepUnloadedRules) for name in self.names]
