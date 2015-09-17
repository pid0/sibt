import pytest
from test.common.servermock import ServerMock
import socket
import time
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from test.common.builders import buildScheduling, anyScheduling, scheduling, \
    optInfo, localLocation
from test.common import mock
import os.path
from py.path import local
from test.common.execmock import ExecMock
from test.common import execmock
import sys
from test.common import relativeToProjectRoot
from test.common.assertutil import strToTest, iterToTest
from sibt.application import configrepo
from sibt.infrastructure import types
from datetime import timedelta
from test.common.bufferinglogger import BufferingLogger

def loadModule(schedulerName, varDir, sibtCall=["/where/sibt/is"],
    logger=None):
  loader = PyModuleSchedulerLoader(PyModuleLoader("testpackage"))
  modulePath = relativeToProjectRoot(os.path.join("sibt", "schedulers", 
    schedulerName))
  return configrepo.loadScheduler(loader, modulePath, schedulerName, 
      configrepo.SchedulerArgs(sibtCall, str(varDir), logger))

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.miscDir = tmpdir.mkdir("misc")
    self.varDir = tmpdir.mkdir("var")
    self.tmpDir = self.miscDir.mkdir("tmp dir")

  def init(self, **kwargs):
    self.mod = loadModule("anacron", varDir=self.varDir, **kwargs)
    self.execs = ExecMock()

  def run(self, schedulings, mockingExecs=True):
    if mockingExecs:
      self.mod.impl.processRunner = self.execs
    self.mod.run(schedulings)
    self.execs.check()
  def check(self, schedulings):
    return self.mod.check(schedulings)
  
  @property
  def optionNames(self):
    return [optInfo.name for optInfo in self.mod.availableOptions]
  @property
  def optionInfos(self):
    return self.mod.availableOptions

  def runWithMockedSibt(self, sibtProgram, schedulings, sibtArgs=[]):
    sibt = self.miscDir / "sibt"
    self.init(sibtCall=[str(sibt)] + sibtArgs)
    sibt.write(sibtProgram)
    sibt.chmod(0o700)
    assert self.check(schedulings) == []
    self.run(schedulings, mockingExecs=False)

  def checkOption(self, optionName, schedulings, matcher):
    self.execs.expect("anacron", execmock.call(
      lambda args: matcher(args[1 + args.index(optionName)])))
    self.run(schedulings)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldInvokeAnacronWithGeneratedTabToCallBackToSibt(fixture):
  testFile = str(fixture.miscDir / "test")
  assert not os.path.isfile(testFile)

  fixture.runWithMockedSibt(r"""#!/usr/bin/env bash
  if [ $1 = --some-global-opt ] && [ "$2" = 'blah "'"'"'foo' ] && \
      [ $3 = sync-uncontrolled ] && [ $4 = -- ] && [ "$5" = 'some*rule' ]; then
    touch {0}
  fi""".format(testFile), [buildScheduling("some*rule")], 
    sibtArgs=["--some-global-opt", "blah \"'foo"])

  assert os.path.isfile(testFile)

def test_shouldPlaceTheAnacronSpoolDirInItsVarDir(fixture):
  fixture.init()
  fixture.checkOption("-S", [anyScheduling()], 
      lambda spoolDir: os.path.isdir(spoolDir) and spoolDir.startswith(
          str(fixture.varDir)))

def test_shouldPutTemporaryTabAndScriptsIntoTmpDirAndDeleteThemAfterwards(
    fixture):
  fixture.init()
  assert "TmpDir" in fixture.optionNames

  def checkTab(tab):
    assert len(fixture.tmpDir.listdir()) > 0
    strToTest(local(tab).read()).shouldIncludeLinePatterns(
        "*rule-id*{0}*".format(str(fixture.tmpDir)))
    return True

  fixture.checkOption("-t", [buildScheduling("rule-id", 
    TmpDir=localLocation(fixture.tmpDir))], checkTab)

  assert len(fixture.tmpDir.listdir()) == 0

def test_shouldRoundTheIntervalsToDaysAndWarnAboutLostParts(fixture):
  logger = BufferingLogger()
  fixture.init(logger=logger)
  assert optInfo("Interval", types.TimeDelta) in fixture.optionInfos

  schedulings = [
      buildScheduling("one-day", Interval=timedelta(hours=22)),
      buildScheduling("two-days", Interval=timedelta(days=2, hours=6)),
      buildScheduling("three-weeks", Interval=timedelta(weeks=3)),
      buildScheduling("no-interval")]

  assert fixture.check(schedulings) == []
  
  def checkTab(tabPath):
    strToTest(local(tabPath).read()).shouldIncludeLinePatterns(
        "3 0 no-interval*",
        "1 0 one-day*",
        "2 0 two-days*",
        "21 0 three-weeks*")
    return True

  fixture.checkOption("-t", schedulings, checkTab)
  logger.string.shouldInclude("one-day", "rounding", "two-days").andAlso.\
      shouldNotInclude("three-weeks")

def test_shouldSupportLoggingSibtOutputToFileBeforeAnacronSeesIt(fixture):
  nameWithQuotesAndSpace = "user'\"s log"
  logFile = fixture.miscDir / nameWithQuotesAndSpace
  fixture.runWithMockedSibt("""#!/usr/bin/env bash
  if [ $3 = not-logging ]; then
    echo lorem ipsum
  fi
  if [ $3 = logging-2 ]; then
    echo dolor sit
  fi
  if [ $3 = logging ]; then
    echo lazy dog
  fi
  echo quick brown fox >&2
  """, [
      buildScheduling("not-logging"),
      buildScheduling("logging", LogFile=localLocation(logFile)),
      buildScheduling("logging-2", LogFile=localLocation(logFile))])

  strToTest(logFile.read()).shouldContainLinePatterns(
      "*quick brown fox",
      "*quick brown fox",
      "*lazy dog",
      "*dolor sit").andAlso.shouldNotInclude("lorem ipsum")

  assert optInfo("LogFile", types.File) in fixture.optionInfos

def test_shouldSupportSysloggingSibtOutput(fixture):
  fixture.init()
  assert optInfo("Syslog", types.Bool) in fixture.optionInfos

  logFile = fixture.tmpdir.join("log")

  message1 = "goes to stdout"
  message2 = "its an error"

  syslogMock = None
  with ServerMock("5024", socket.SOCK_DGRAM) as syslogMock:
    fixture.runWithMockedSibt(
    """#!/usr/bin/env bash
    echo {0}
    echo {1} >&2""".format(message1, message2), [buildScheduling(
      LogFile=localLocation(logFile), Syslog=True,
      SyslogTestOpts="--server localhost --port 5024")])
    time.sleep(0.2)

  strToTest(syslogMock.receivedBytes.decode("utf-8")).shouldInclude(
      "sibt",
      message1,
      message2)
  strToTest(logFile.read()).shouldInclude(
      message1, message2)

def test_shouldHaveAnOptionThatTakesBashCodeToExecuteWhenSibtFails(fixture):
  testFile = fixture.miscDir / "test's file"
  normalSchedulingRunFlagFile = str(fixture.miscDir / "flag")
  logFile = fixture.miscDir / "log"

  executingScheduling = scheduling().withOptions(
      ExecOnFailure='echo failure; echo "$r" >"{0}"'.format(testFile),
      LogFile=localLocation(logFile))

  fixture.runWithMockedSibt("""#!/usr/bin/env bash
  if [ $3 = fails ]; then
    exit 1
  else
    touch '{0}'
  fi""".format(normalSchedulingRunFlagFile), [
      executingScheduling.withRuleName("fails").build(),
      executingScheduling.withRuleName("doesnt").build()])

  assert os.path.isfile(normalSchedulingRunFlagFile)
  assert testFile.read() == "fails\n"
  assert logFile.read() == "failure\n"

  assert "ExecOnFailure" in fixture.optionNames

def test_shouldCheckSyntaxOfExecOnFailureCodeWithoutExecutingIt(fixture):
  fixture.init()
  flagFile = str(fixture.miscDir / "flag")

  erroneousCode = "touch {0}\n(echo foo".format(flagFile)

  iterToTest(fixture.check([buildScheduling("touching",
    ExecOnFailure=erroneousCode)])).shouldContainMatching(
          lambda error: strToTest(error).shouldInclude("unexpected", 
            "ExecOnFailure", "syntax", "touching"))
  assert not os.path.isfile(flagFile)

def test_shouldNotSwallowExitCodeOfSibtButPassItOnToAnacron(fixture, capfd):
  fixture.runWithMockedSibt(r"""#!/usr/bin/env bash
  exit 4""", [anyScheduling()])

  _, stderr = capfd.readouterr()
  assert "status: 4" in stderr

def test_shouldHaveAnInterfaceToAnacronsStartHoursRange(fixture):
  fixture.init()

  assert "AllowedHours" in fixture.optionNames
  def checkTab(tabPath):
    strToTest(local(tabPath).read()).shouldIncludeLinePatterns(
        "*START_HOURS_RANGE=6-20")
    return True
  schedulings = [buildScheduling(AllowedHours="6-20"), anyScheduling()]
  fixture.checkOption("-t", schedulings, checkTab)

def test_shouldCheckIfAllowedHoursSettingHasTheRightSyntax(fixture):
  fixture.init()

  def assertIsWrongSyntax(setting):
    ruleName = "bad-conf"
    iterToTest(fixture.check([buildScheduling(ruleName, 
      AllowedHours=setting)])).shouldIncludeMatching(
          lambda error: strToTest(error).shouldInclude(
            ruleName, "syntax", "AllowedHours", setting))

  assertIsWrongSyntax("foo")
  assertIsWrongSyntax("5-")
  assertIsWrongSyntax("5-7 foo")
  assertIsWrongSyntax("7-5")
  assertIsWrongSyntax("0-25")

  assert fixture.check([buildScheduling(AllowedHours="0-19")]) == []

def test_shouldReturnAsManyCheckErrorsAsItCanFind(fixture):
  fixture.init()

  assert len(fixture.check([buildScheduling(
    ExecOnFailure="(", AllowedHours="bar")])) > 1

def test_shouldManageToBeInitializedMultipleTimesWithTheSameFolders(fixture):
  fixture.init()
  fixture.init()
