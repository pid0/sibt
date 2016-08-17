from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.configuration.cachinginifilelistreader import CachingIniFileListReader
from sibt.configuration import dirbasedrulesreader
from sibt.domain.defaultvaluesynchronizer import DefaultValueSynchronizer
from sibt.infrastructure.cachingsynchronizer import CachingSynchronizer
from sibt.infrastructure.functionmodulesynchronizer import \
    FunctionModuleSynchronizer
from sibt.configuration.exceptions import MissingConfigValuesException, \
    ConfigConsistencyException
from sibt.infrastructure import collectFilesInDirs
import sys
from sibt.configuration.rulefromstringoptionsreader import \
    RuleFromStringOptionsReader
from sibt.domain.rulefactory import RuleFactory
from sibt.application.runner import Runner
from sibt.application.hashbangawareprocessrunner import \
    HashbangAwareProcessRunner
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.application.exceptions import RuleNameMismatchException
from sibt.infrastructure.runnablefilefunctionmodule import \
    RunnableFileFunctionModule
from sibt.configuration.optionvaluesparser import OptionValuesParser
from collections import namedtuple
import os

SchedulerArgs = namedtuple("SchedulerArgs", [
    "sibtInvocation", "varDir", "logger"])

def readSynchronizers(dirs, processRunner):
  def load(path, fileName):
    try:
      return loadSynchronizer(processRunner, path, fileName)
    except ConfigConsistencyException:
      return None

  return collectFilesInDirs(dirs, load)

def loadSynchronizer(processRunner, executablePath, name):
  functionModule = RunnableFileFunctionModule(processRunner, executablePath)
  return CachingSynchronizer(DefaultValueSynchronizer(
    FunctionModuleSynchronizer(functionModule, name)))

def loadScheduler(loader, modulePath, name, initArgs):
  return loader.loadFromFile(modulePath, name, (initArgs,))

def makeSchedulerVarDir(paths, schedulerName):
  schedulerVarDir = os.path.join(paths.varDir, schedulerName)
  if not os.path.isdir(schedulerVarDir):
    os.mkdir(schedulerVarDir)
  return schedulerVarDir

def readSchedulers(dirs, loader, schedulerWrapper, initArgs,
    paths, makeErrorLoggerWithPrefix):
  return collectFilesInDirs(dirs, lambda path, fileName:
      schedulerWrapper(loadScheduler(loader, path, fileName, 
        initArgs._replace(logger=makeErrorLoggerWithPrefix(
          "sibt({0})".format(fileName)),
          varDir=makeSchedulerVarDir(paths, fileName)))))

def readRuleLoaders(rulesDir, enabledDir, factory, prefix):
  reader = DirBasedRulesReader(CachingIniFileListReader(rulesDir,
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
      moduleLoader, sibtInvocation, schedulerWrapper, 
      makeErrorLoggerWithPrefix):
    processRunnerWrapper = createHashbangAwareProcessRunner(paths.runnersDir,
        processRunner)

    synchronizers = readSynchronizers([paths.synchronizersDir, 
      paths.readonlySynchronizersDir] + ([sysPaths.synchronizersDir] if 
        readSysConf else []), processRunnerWrapper)
    schedulers = readSchedulers(
        [paths.schedulersDir, paths.readonlySchedulersDir] + 
        ([sysPaths.schedulersDir] if readSysConf else []), 
        PyModuleSchedulerLoader(moduleLoader), schedulerWrapper,
        SchedulerArgs(sibtInvocation, None, None), paths,
        makeErrorLoggerWithPrefix)

    factory = RuleFromStringOptionsReader(RuleFactory(),
        OptionValuesParser(), schedulers, synchronizers)
    userRules = readRuleLoaders(paths.rulesDir, paths.enabledDir, factory, "")
    sysRules = [] if not readSysConf else readRuleLoaders(sysPaths.rulesDir, 
        sysPaths.enabledDir, factory, "+")

    return clazz(schedulers, synchronizers, userRules, sysRules)

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
    return [self.getRule(name, keepUnloadedRules) for name in self.names]
