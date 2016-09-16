from sibt.domain.scheduling import Scheduling
from sibt.application.runner import Runner
from datetime import datetime, timezone, timedelta
from random import random
import os.path
from test.common import mock
from sibt.infrastructure.location import LocalLocation, RemoteLocation
from sibt.domain.version import Version
import re
from sibt.domain.port import Port
from sibt.configuration.optionvaluesparser import parseLocation
from sibt.domain.syncrule import LocCheckLevel
from sibt.domain.optioninfo import OptionInfo
from sibt.infrastructure import types
from sibt.domain.synchronizeroptions import SynchronizerOptions 
from sibt.domain.ruleset import RuleSet
from sibt.domain.schedulinglogging import SchedulingLogging, SchedulingResult
from test.common.presetcyclingclock import PresetCyclingClock
from sibt.application.execenvironment import ExecEnvironment

def randstring():
  return str(random())[2:] 
  
def withRandstring(string):
  return string + randstring()

class SchedulingBuilder(object):
  def __init__(self):
    self.ruleName = withRandstring("any-rule")
    self.options = dict()

  def withRuleName(self, name):
    self.ruleName = name
    return self

  def withOption(self, key, value):
    self.options[key] = value
    return self
  def withOptions(self, **options):
    self.options = dict(options)
    return self
    
  def build(self):
    return Scheduling(self.ruleName, self.options)

def execEnvironment(syncUncontrolledCall=[],
    logger=None,
    logSubProcessWith=lambda *args, **kwargs: None):
  return ExecEnvironment(syncUncontrolledCall, logger, logSubProcessWith)

def anyScheduling(): return buildScheduling()
def buildScheduling(ruleName=None, **options):
  retBuilder = scheduling()
  if ruleName is not None:
    retBuilder = retBuilder.withRuleName(ruleName)
  return retBuilder.withOptions(**options).build()
def scheduling():
  return SchedulingBuilder()

def existingRunner(tmpdir, name): 
  path = tmpdir.join(name)
  path.write("#!/bin/sh")
  return str(path), Runner(name, str(path))

def anyUTCDateTime():
  return datetime.now(timezone.utc) - timedelta(days=int(random() * 330))

def orderedDateTimes(numberOfDateTimes):
  return [
      datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc),
      datetime(2002, 12, 31, 23, 59, 59, 0, timezone.utc),
      datetime(2003, 12, 31, 23, 59, 59, 0, timezone.utc),
      datetime(2005, 12, 31, 23, 59, 59, 0, timezone.utc)][:numberOfDateTimes]

def clockWithOrderedTimes(numberOfDateTimes):
  return PresetCyclingClock(*orderedDateTimes(numberOfDateTimes))

def constantTimeClock(dateTime=None):
  if dateTime is None:
    dateTime = anyUTCDateTime()
  return PresetCyclingClock(dateTime)

def schedulingResult(endTime=None):
  if endTime is None:
    endTime = anyUTCDateTime()

  return SchedulingResult(endTime, True)

def schedulingLogging(startTime=None):
  if startTime is None:
    startTime = anyUTCDateTime()

  return SchedulingLogging(startTime, "foobarüã", schedulingResult())

def port(supportedProtocols=["file"], isWrittenTo=False):
  return Port(supportedProtocols, isWrittenTo)

def optInfo(name, optionType=types.String):
  return OptionInfo(name, optionType)

def mkSyncerOpts(**options):
  return SynchronizerOptions.fromDict(options)

def location(path="/any"):
  return localLocation(path)
def localLocation(path="/any"):
  return LocalLocation(str(path))
def remoteLocation(protocol="rsync", login="", host="host", port="", 
    path="/"):
  return RemoteLocation(protocol, login, host, port, path)

def mockSched(*args, sharedOptions=[], **kwargs):
  ret = fakeConfigurable(*args, **kwargs)
  ret.availableSharedOptions = sharedOptions
  return ret
def fakeConfigurable(*args, **kwargs):
  return mockSyncer(*args, **kwargs)
def mockSyncer(name="foo", availableOptions=[],
    ports=[port(["file"], isWrittenTo=False), 
      port(["file"], isWrittenTo=True)]):
  ret = mock.mock(name)
  ret.name = name
  ret.availableOptions = list(availableOptions)
  ret.ports = ports
  ret.onePortMustHaveFileProtocol = False
  return ret

def version(rule, time=anyUTCDateTime()):
  return Version(rule, time)

def ruleSet(*rules):
  return RuleSet(rules)

def mockRule(name="foo", options=None, scheduler=None, loc1="/tmp/1", 
    loc2="/tmp/2", writeLocs=[2], schedOpts=dict(), syncerName="foo",
    syncerCheckErrors=[]):
  ret = mock.mock(name)
  if options is None:
    options = dict(LocCheckLevel=LocCheckLevel.Default)
  ret.options = options
  ret.name = name
  ret.schedulerOptions = schedOpts
  ret.scheduler = scheduler
  ret.scheduling = object()
  ret.locs = [parseLocation(str(loc1)), parseLocation(str(loc2))]
  ret.writeLocs = [parseLocation(str(loc1))] if 1 in writeLocs else [] + \
      [parseLocation(str(loc2))] if 2 in writeLocs else []
  ret.nonWriteLocs = [parseLocation(str(loc1))] if 1 not in writeLocs else \
      [] + [parseLocation(str(loc2))] if 2 not in writeLocs else []
  ret.syncerName = syncerName
  ret.syncerCheckErrors = syncerCheckErrors
  return ret

def writeFileTree(folder, fileList):
  createdFileList = []

  def doWriteFileTree(folder, fileList, createdFileList):
    def assignIndex(createdFileList, index, createdFile):
      createdFileList.extend((index - (len(createdFileList) - 1)) * [None])
      createdFileList[index] = createdFile

    def makeFile(isFolder, folder, fileDesc):
      nameAndIndex = re.search(r"^(.*)( \[(\d+)\])$", fileDesc)
      fileName = nameAndIndex.group(1) if nameAndIndex else fileDesc
      if isFolder:
        ret = folder.mkdir(fileName) if fileName != "." else folder
      elif " -> " in fileName:
        symlinkName, symlinkDest = fileName.split(" -> ")
        ret = folder.join(symlinkName)
        ret.mksymlinkto(symlinkDest)
      else:
        ret = folder.join(fileName)
        ret.write("")

      if nameAndIndex:
        assignIndex(createdFileList, int(nameAndIndex.group(3)) - 1, ret)
      return ret

    newFolder = makeFile(True, folder, fileList[0])
    for subFile in fileList[1:]:
      if isinstance(subFile, list):
        doWriteFileTree(newFolder, subFile, createdFileList)
      else:
        makeFile(False, newFolder, subFile)

  doWriteFileTree(folder, fileList, createdFileList)
  return createdFileList

