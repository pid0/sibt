import os.path
from datetime import timedelta, datetime, timezone

from test.common.schedulertest import SchedulerTestFixture
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from test.common import relativeToProjectRoot
from test.common.builders import schedulingSet, buildScheduling
from test.common.presetcyclingclock import PresetCyclingClock
from sibt.application import configrepo
from sibt.infrastructure import timehelper

testPackageCounter = 0

def loadModule(schedulerName, varDir, sibtCall=["/where/sibt/is"],
    logger=None, clock=None):
  global testPackageCounter
  testPackageCounter = testPackageCounter + 1
  packageName = "testpackage{0}".format(testPackageCounter)
  loader = PyModuleSchedulerLoader(PyModuleLoader(packageName))
  modulePath = relativeToProjectRoot(os.path.join("sibt", "schedulers", 
    schedulerName))
  return configrepo.loadSchedulerFromModule(loader, modulePath, schedulerName, 
      configrepo.SchedulerArgs(sibtCall, str(varDir), logger, clock))

def toUTC(localDateTime):
  if localDateTime is None:
    return localDateTime
  return timehelper.toUTC(localDateTime.replace(tzinfo=None))

BeginningOf1985 = datetime(1985, 1, 1, 0, 0, 0, 0)

class LeafSchedulerTestFixture(SchedulerTestFixture):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.miscDir = tmpdir.mkdir("misc")
    self.varDir = tmpdir.mkdir("var")
    self.clock = PresetCyclingClock(datetime.now(timezone.utc))

  def makeSched(self, **kwargs):
    return loadModule(self.moduleName, varDir=self.varDir, clock=self.clock, 
        **kwargs)

  def setCurrentLocalTime(self, currentLocalTime):
    self.clock.dateTimes = [toUTC(currentLocalTime)]
  
  def scheduleWithMockedSibt(self, sibtProgram, schedulings, sibtArgs=[]):
    assert self.check(schedulings) == []
    sibt = self.miscDir / "sibt"
    sched = self.makeSched(sibtCall=[str(sibt)] + sibtArgs)
    sibt.write(sibtProgram)
    sibt.chmod(0o700)
    sched.schedule(schedulingSet(schedulings))

  def nextExecutionLocalTime(self, schedulingOptions, lastLocalTime):
    ret = self.makeSched().nextExecutionTime(
        buildScheduling(lastTime=toUTC(lastLocalTime), **schedulingOptions))
    assert ret.tzinfo == timezone.utc
    return ret.astimezone().replace(tzinfo=None)

class LeafSchedulerTest(object):
  def test_shouldCallSibtWithTheRightArgsForEachScheduling(self, fixture):
    flagFile = str(fixture.miscDir / "test")
    assert not os.path.isfile(flagFile)

    fixture.scheduleWithMockedSibt(r"""#!/usr/bin/env bash
    if [ $1 = --some-global-opt ] && [ "$2" = 'blah "'"'"'foo' ] && \
        [ $3 = execute-rule ] && [ $4 = -- ] && [ "$5" = 'some*rule' ]; then
      touch {0}
    fi""".format(flagFile), [buildScheduling("some*rule")], 
      sibtArgs=["--some-global-opt", "blah \"'foo"])

    assert os.path.isfile(flagFile)
