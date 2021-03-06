# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
from sibt.infrastructure.filesdbexecutionslog import FilesDBExecutionsLog
from sibt.application.rulesfinder import RulesFinder
from sibt.application import sshfsautomountingsynchronizer as sshfssyncer
from sibt.configuration.configurablelist import ConfigurableList, \
    LazyConfigurable
from collections import namedtuple
import os

SchedulerArgs = namedtuple("SchedulerArgs", [
    "sibtInvocation", "varDir", "logger", "clock"])
SysRulePrefix = "+"

def readSynchronizers(dirs, processRunner):
  def load(path, fileName):
    return LazyConfigurable(fileName,
        lambda: loadSynchronizer(processRunner, path, fileName))

  return ConfigurableList(collectFilesInDirs(dirs, load))

def loadSynchronizer(processRunner, executablePath, name):
  try:
    functionModule = RunnableFileFunctionModule(processRunner, executablePath)
    ret = FunctionModuleSynchronizer(functionModule, name)
    ret = DefaultValueSynchronizer(ret)
    ret = CachingSynchronizer(ret)
    if sshfssyncer.isExtensible(ret):
      ret = sshfssyncer.SSHFSAutoMountingSynchronizer(ret, processRunner)
    return ret
  except ConfigConsistencyException:
    return None

def loadSchedulerFromModule(loader, modulePath, name, initArgs):
  return loader.loadFromFile(modulePath, name, (initArgs,))

def makeSchedulerVarDir(paths, schedulerName):
  schedulerVarDir = os.path.join(paths.varDir, schedulerName)
  if not os.path.isdir(schedulerVarDir):
    os.mkdir(schedulerVarDir)
  return schedulerVarDir

def readSchedulers(dirs, loader, schedulerWrapper, initArgs,
    paths, makeErrorLoggerWithPrefix):
  def loadScheduler(path, name):
    newInitArgs = initArgs._replace(
        logger=makeErrorLoggerWithPrefix("sibt ({0})".format(name)),
        varDir=makeSchedulerVarDir(paths, name))
    ret = loadSchedulerFromModule(loader, path, name, newInitArgs)
    return schedulerWrapper(ret)

  return ConfigurableList(collectFilesInDirs(dirs, lambda path, fileName:
      LazyConfigurable(fileName, lambda: loadScheduler(path, fileName))))

def readRuleLoaders(rulesDir, includeDirs, enabledDir, factory, prefix):
  reader = DirBasedRulesReader(CachingIniFileListReader(
    [rulesDir] + includeDirs, dirbasedrulesreader.AllowedSections), 
    rulesDir, enabledDir, factory, prefix)
  return list(reader.read())

def createHashbangAwareProcessRunner(runnersDir, processRunner):
  runners = collectFilesInDirs([runnersDir], 
      lambda path, fileName: Runner(fileName, path))
  return HashbangAwareProcessRunner(runners, processRunner)
  
def readRulesIntoFinder(paths, sysPaths, userFactory, sysFactory,
    sysRuleFilter, readUserConf=True, readSysConf=True):
  userRules = [] if not readUserConf else readRuleLoaders(paths.rulesDir, 
      [paths.readonlyIncludesDir], paths.enabledDir, userFactory, "")
  sysRules = [] if not readSysConf else readRuleLoaders(sysPaths.rulesDir, 
      [sysPaths.readonlyIncludesDir], sysPaths.enabledDir, sysFactory, 
      SysRulePrefix)

  return RulesFinder(RulesRepo(userRules), RulesRepo(sysRules), sysRuleFilter)

def isSysRule(rule):
  return rule.name.startswith(SysRulePrefix)

class _EmptyLog(object):
  def executionsOfRules(self, _):
    return dict()

def openLogs(paths, sysPaths):
  userLog = sysLog = _EmptyLog()
  if paths is not None:
    userLog = FilesDBExecutionsLog(paths.logDir)
  if sysPaths is not None:
    sysLog = FilesDBExecutionsLog(sysPaths.logDir, 
        ruleNamePrefix=SysRulePrefix)
  return userLog, sysLog

class ConfigRepo(object):
  def __init__(self, schedulers, synchronizers, rulesFinder):
    self.schedulers = schedulers
    self.synchronizers = synchronizers
    self.rulesFinder = rulesFinder

  @classmethod
  def load(clazz, paths, sysPaths, readSysConf, processRunner, clock,
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
        SchedulerArgs(sibtInvocation, None, None, clock), paths,
        makeErrorLoggerWithPrefix)

    userLog, sysLog = openLogs(paths, sysPaths)

    valuesParser = OptionValuesParser()
    userFactory = RuleFromStringOptionsReader(RuleFactory(userLog),
        valuesParser, schedulers, synchronizers)
    sysFactory = RuleFromStringOptionsReader(RuleFactory(sysLog),
        valuesParser, schedulers, synchronizers)
    rulesFinder = readRulesIntoFinder(paths, sysPaths, userFactory,
        sysFactory, sysRuleFilter, readSysConf=readSysConf)

    return clazz(schedulers, synchronizers, rulesFinder)

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
