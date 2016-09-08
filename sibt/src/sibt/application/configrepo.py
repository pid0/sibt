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
from sibt.infrastructure.filesdbschedulingslog import FilesDBSchedulingsLog
from sibt.application.rulesfinder import RulesFinder
from collections import namedtuple
import os

SchedulerArgs = namedtuple("SchedulerArgs", [
    "sibtInvocation", "varDir", "logger"])
SysRulePrefix = "+"

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
  
def readRulesIntoFinder(paths, sysPaths, factory, sysRuleFilter,
    readUserConf=True, readSysConf=True):
  userRules = [] if not readUserConf else readRuleLoaders(paths.rulesDir, 
      paths.enabledDir, factory, "")
  sysRules = [] if not readSysConf else readRuleLoaders(sysPaths.rulesDir, 
      sysPaths.enabledDir, factory, "+")

  return RulesFinder(RulesRepo(userRules), RulesRepo(sysRules), sysRuleFilter)

def isSysRule(rule):
  return rule.name.startswith(SysRulePrefix)

class _EmptyLog(object):
  def loggingsOfRules(self, _):
    return dict()

def openLogs(paths, sysPaths):
  userLog = sysLog = _EmptyLog()
  if paths is not None:
    userLog = FilesDBSchedulingsLog(paths.logDir)
  if sysPaths is not None:
    sysLog = FilesDBSchedulingsLog(sysPaths.logDir, 
        ruleNamePrefix=SysRulePrefix)
  return userLog, sysLog

class ConfigRepo(object):
  def __init__(self, schedulers, synchronizers, rulesFinder, userLog):
    self.schedulers = schedulers
    self.synchronizers = synchronizers
    self.rulesFinder = rulesFinder
    self.userLog = userLog

  @classmethod
  def load(clazz, paths, sysPaths, readSysConf, processRunner, 
      moduleLoader, sibtInvocation, schedulerWrapper, 
      makeErrorLoggerWithPrefix, sysRuleFilter):
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

    #userLog, sysLog = openLogs(paths, sysPaths)
    userLog = FilesDBSchedulingsLog(paths.logDir)
    #sysLog = FilesDBSchedulingsLog(paths.logDir)

    factory = RuleFromStringOptionsReader(RuleFactory(),
        OptionValuesParser(), schedulers, synchronizers)
    rulesFinder = readRulesIntoFinder(paths, sysPaths, factory, sysRuleFilter,
        readSysConf=readSysConf)

    return clazz(schedulers, synchronizers, rulesFinder, userLog)

class RulesRepo(object):
  def __init__(self, lazyRules):
    self._namesToRules = dict((rule.name, rule) for rule in lazyRules)
    self._ruleRead = dict((rule.name, False) for rule in lazyRules)
    self.names = list(self._namesToRules.keys())
    self.enabledNames = [rule.name for rule in lazyRules if rule.enabled]
    self.disabledNames = [rule.name for rule in lazyRules if not rule.enabled]
  
  def getRule(self, name, keepUnloaded):
    rule = self.getRuleWithoutLoading(name)
    if not self._ruleRead[name]:
      try:
        self._namesToRules[name] = rule.load()
        self._ruleRead[name] = True
      except MissingConfigValuesException:
        if not rule.enabled and keepUnloaded:
          return rule
        raise
    return self.getRuleWithoutLoading(name)
  
  def getRuleWithoutLoading(self, name):
    try:
      return self._namesToRules[name]
    except KeyError:
      raise RuleNameMismatchException(name)
