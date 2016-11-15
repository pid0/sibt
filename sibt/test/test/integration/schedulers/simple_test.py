import pytest
import os
import time
from test.common.builders import buildScheduling
from test.integration.schedulers.leafschedulertest import LeafSchedulerTest, \
    LeafSchedulerTestFixture, BeginningOf1985, toUTC
from datetime import timedelta, datetime

class Fixture(LeafSchedulerTestFixture):
  moduleName = "simple"
  def __init__(self, tmpdir):
    super().__init__(tmpdir)
    self.varDir = "/does-not-exist"

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)


BeginningOf1985 = datetime(1985, 1, 1, 0, 0, 0, 0)

class Test_SimpleSchedTest(LeafSchedulerTest):
  def test_shouldExecuteAllScheduledRulesAtOnce(self, fixture):
    names = ["foo", "bar", "baz", "quux", "foobar"]
    schedulings = [buildScheduling(name) for name in names]
    flagFiles = [fixture.miscDir / name for name in names]

    startSeconds = time.perf_counter()
    fixture.scheduleWithMockedSibt(r"""#!/usr/bin/env bash
      sleep 0.25
      touch "{0}"/"$3" """.format(fixture.miscDir), schedulings)
    elapsedSeconds = time.perf_counter() - startSeconds
    assert elapsedSeconds > 0.25
    assert elapsedSeconds < 0.5

    for flagFile in flagFiles:
      assert os.path.isfile(str(flagFile))
      
  def test_shouldScheduleTheNextAtLastTimePlusIntervalDisregardingTimeOfDay(
      self, fixture):
    assert "Interval" in fixture.optionNames
    fixture.setCurrentLocalTime(BeginningOf1985)

    assert fixture.nextExecutionLocalTime(dict(Interval=timedelta(
      days=2, hours=3, minutes=32)), datetime(2000, 1, 1, 12, 4, 0, 0)) == \
          datetime(2000, 1, 3, 3, 32, 0, 0)

    assert fixture.nextExecutionLocalTime(dict(), None) == BeginningOf1985

  def test_shouldNotRemoveTimeOfDayIfIntervalIsLessThanADay(self, fixture):
    fixture.setCurrentLocalTime(BeginningOf1985)

    assert fixture.nextExecutionLocalTime(dict(Interval=timedelta(minutes=5)),
        datetime(2000, 1, 1, 8, 25, 0, 0)) == datetime(2000, 1, 1, 8, 30, 0, 0)

  def test_shouldNotReturnATimeInThePastAsNextExecutionTime(self, fixture):
    fixture.setCurrentLocalTime(BeginningOf1985)

    assert fixture.nextExecutionLocalTime(dict(Interval=timedelta(days=10)), 
        datetime(1984, 1, 1, 0, 0, 0, 0)) == BeginningOf1985
  
  def test_shouldExecuteOncePastTheNextExecutionTime(self, fixture):
    sibtExecutedFlag = fixture.miscDir / "flag"
    lastTime = toUTC(BeginningOf1985)
    def schedule():
      fixture.scheduleWithMockedSibt(r"""#!/usr/bin/env bash
        touch "{0}" """.format(sibtExecutedFlag), [
        buildScheduling(lastTime=lastTime, Interval=timedelta(days=2))])

    fixture.setCurrentLocalTime(datetime(1985, 1, 2, 0, 0, 0, 0))
    schedule()
    assert not os.path.isfile(str(sibtExecutedFlag))

    fixture.setCurrentLocalTime(datetime(1985, 1, 3, 0, 0, 0, 0))
    schedule()
    assert os.path.isfile(str(sibtExecutedFlag))
