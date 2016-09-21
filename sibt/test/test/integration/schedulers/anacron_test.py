import pytest
import socket
import time
from test.common.schedulertest import SchedulerTestFixture
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from test.common.builders import buildScheduling, anyScheduling, scheduling, \
    optInfo, localLocation, schedulingSet
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
from datetime import timedelta, datetime, timezone
from test.common.bufferingerrorlogger import BufferingErrorLogger

testPackageCounter = 0

def loadModule(schedulerName, varDir, sibtCall=["/where/sibt/is"],
    logger=None):
  global testPackageCounter
  testPackageCounter = testPackageCounter + 1
  packageName = "testpackage{0}".format(testPackageCounter)
  loader = PyModuleSchedulerLoader(PyModuleLoader(packageName))
  modulePath = relativeToProjectRoot(os.path.join("sibt", "schedulers", 
    schedulerName))
  return configrepo.loadScheduler(loader, modulePath, schedulerName, 
      configrepo.SchedulerArgs(sibtCall, str(varDir), logger))

class Fixture(SchedulerTestFixture):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.miscDir = tmpdir.mkdir("misc")
    self.varDir = tmpdir.mkdir("var")
    self.tmpDir = self.miscDir.mkdir("tmp dir")

  def init(self, **kwargs):
    self.mod = self.makeSched(**kwargs)
    self.execs = ExecMock()
  
  def makeSched(self, **kwargs):
    return loadModule("anacron", varDir=self.varDir, **kwargs)

  def schedule(self, schedulings, mockingExecs=True):
    if mockingExecs:
      self.mod.impl.processRunner = self.execs
    self.mod.schedule(schedulingSet(schedulings))
    self.execs.check()
  
  def scheduleWithMockedSibt(self, sibtProgram, schedulings, sibtArgs=[]):
    sibt = self.miscDir / "sibt"
    self.init(sibtCall=[str(sibt)] + sibtArgs)
    sibt.write(sibtProgram)
    sibt.chmod(0o700)
    assert self.check(schedulings) == []
    self.schedule(schedulings, mockingExecs=False)

  def checkOption(self, optionName, schedulings, matcher):
    self.execs.expect("anacron", execmock.call(
      lambda args: matcher(args[1 + args.index(optionName)])))
    self.schedule(schedulings)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldInvokeAnacronWithGeneratedTabToCallBackToSibt(fixture):
  testFile = str(fixture.miscDir / "test")
  assert not os.path.isfile(testFile)

  fixture.scheduleWithMockedSibt(r"""#!/usr/bin/env bash
  if [ $1 = --some-global-opt ] && [ "$2" = 'blah "'"'"'foo' ] && \
      [ $3 = execute-rule ] && [ $4 = -- ] && [ "$5" = 'some*rule' ]; then
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
  assert "TmpDir" in fixture.optionNames

  fixture.init()

  def checkTab(tab):
    assert len(fixture.tmpDir.listdir()) > 0
    strToTest(local(tab).read()).shouldIncludeLinePatterns("*rule-id*")
    return True

  fixture.checkOption("-t", [buildScheduling("rule-id", 
    TmpDir=localLocation(fixture.tmpDir))], checkTab)

  assert len(fixture.tmpDir.listdir()) == 0

def test_shouldRoundTheIntervalsToDaysAndWarnAboutLostParts(fixture):
  assert optInfo("Interval", types.TimeDelta) in fixture.optionInfos

  logger = BufferingErrorLogger()
  fixture.init(logger=logger)

  schedulings = [
      buildScheduling("one-day", Interval=timedelta(hours=22)),
      buildScheduling("two-days", Interval=timedelta(days=2, hours=6)),
      buildScheduling("three-weeks", Interval=timedelta(weeks=3)),
      buildScheduling("no-interval")]

  def shouldHaveWarned():
    logger.string.shouldInclude("one-day", "rounding", "two-days").andAlso.\
        shouldNotInclude("three-weeks")
    logger.clear()

  assert fixture.check(schedulings, logger=logger) == []
  shouldHaveWarned()
  
  def checkTab(tabPath):
    strToTest(local(tabPath).read()).shouldIncludeLinePatterns(
        "3 0 no-interval*",
        "1 0 one-day*",
        "2 0 two-days*",
        "21 0 three-weeks*")
    return True

  fixture.checkOption("-t", schedulings, checkTab)
  shouldHaveWarned()

def test_shouldNotSwallowExitCodeOfSibtButPassItOnToAnacron(fixture, capfd):
  fixture.scheduleWithMockedSibt(r"""#!/usr/bin/env bash
  exit 4""", [anyScheduling()])

  _, stderr = capfd.readouterr()
  assert "status: 4" in stderr

def test_shouldCopyAnacronsBehaviorWhenDeterminingTheNextExecutionTime(fixture):
  fixture.init()

  assert fixture.mod.nextExecutionTime(
      buildScheduling(Interval=timedelta(days=2)),
      datetime(2010, 1, 1, 0, 0, 0, 0, timezone.utc)) == datetime(
          2010, 1, 3, 0, 0, 0, 0, timezone.utc)

  assert fixture.mod.nextExecutionTime(
      buildScheduling(Interval=timedelta(days=3, hours=5)),
      datetime(2010, 1, 1, 20, 0, 0, 0, timezone.utc)) == datetime(
          2010, 1, 4, 0, 0, 0, 0, timezone.utc)

  assert abs(fixture.mod.nextExecutionTime(buildScheduling(), None) -
      datetime.now(timezone.utc)) < timedelta(seconds=1)

def test_shouldHaveAnInterfaceToAnacronsStartHoursRange(fixture):
  assert "AllowedHours" in fixture.optionNames

  fixture.init()

  def checkTab(tabPath):
    strToTest(local(tabPath).read()).shouldIncludeLinePatterns(
        "*START_HOURS_RANGE=6-20")
    return True
  schedulings = [buildScheduling(AllowedHours="6-20")]
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

  schedulings = [
      buildScheduling(AllowedHours="bar"),
      buildScheduling(AllowedHours="3")]

  assert len(fixture.check(schedulings)) > 1

def test_shouldManageToBeInitializedMultipleTimesWithTheSameFolders(fixture):
  fixture.init()
  fixture.init()
