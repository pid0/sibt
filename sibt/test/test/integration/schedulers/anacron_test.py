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

import pytest
import socket
import time
from test.common.schedulertest import SchedulerTestFixture
from test.integration.schedulers.leafschedulertest import LeafSchedulerTest, \
    LeafSchedulerTestFixture, BeginningOf1985
from test.common.builders import buildScheduling, anyScheduling, scheduling, \
    optInfo, localLocation, schedulingSet, constantTimeClock, In1985
from test.common import mock
import os.path
from py.path import local
from test.common.execmock import ExecMock
from test.common import execmock
import sys
from test.common.assertutil import strToTest, iterToTest
from sibt.infrastructure import types
from datetime import timedelta, datetime, timezone
from test.common.bufferingerrorlogger import BufferingErrorLogger

AnyInterval = timedelta(days=3)

class Fixture(LeafSchedulerTestFixture):
  moduleName = "anacron"
  def __init__(self, tmpdir):
    super().__init__(tmpdir)
    self.tmpDir = self.miscDir.mkdir("tmp dir")

  def init(self, **kwargs):
    self.mod = self.makeSched(**kwargs)
    self.execs = ExecMock()
  
  def schedule(self, schedulings):
    self.mod.impl.processRunner = self.execs
    self.mod.schedule(schedulingSet(schedulings))
    self.execs.check()

  def checkOption(self, optionName, schedulings, matcher):
    self.execs.expect("anacron", execmock.call(
      lambda args: matcher(args[1 + args.index(optionName)])))
    self.schedule(schedulings)
  
  def nextExecutionLocalTime(self, interval, lastLocalTime, allowedHours=None):
    options = dict(Interval=interval)
    if allowedHours is not None:
      options["AllowedHours"] = allowedHours
    return super().nextExecutionLocalTime(options, lastLocalTime)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_AnacronTest(LeafSchedulerTest):
  def test_shouldPlaceTheAnacronSpoolDirInItsVarDir(self, fixture):
    fixture.init()
    fixture.checkOption("-S", [anyScheduling()], 
        lambda spoolDir: os.path.isdir(spoolDir) and spoolDir.startswith(
            str(fixture.varDir)))

  def test_shouldPutTemporaryTabAndScriptsIntoTmpDirAndDeleteThemAfterwards(
      self, fixture):
    assert "TmpDir" in fixture.optionNames

    fixture.init()

    def checkTab(tab):
      assert len(fixture.tmpDir.listdir()) > 0
      strToTest(local(tab).read()).shouldIncludeLinePatterns("*rule-id*")
      return True

    fixture.checkOption("-t", [buildScheduling("rule-id", 
      TmpDir=localLocation(fixture.tmpDir))], checkTab)

    assert len(fixture.tmpDir.listdir()) == 0

  def test_shouldHaveAnOptionThatCausesItToWriteTheTabWithoutExecuting(
      self, fixture):
    assert "OutputTabFile" in fixture.optionNames
    fixture.init()
    tabFile = fixture.tmpdir / "tab"

    fixture.schedule([
      buildScheduling("foo", OutputTabFile=localLocation(tabFile)),
      buildScheduling("bar", OutputTabFile=localLocation(tabFile))])

    strToTest(tabFile.read()).shouldIncludeLinePatterns("*foo*", "*bar*")

  def test_shouldRoundTheIntervalsToDaysAndWarnAboutLostParts(self, fixture):
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

  def test_shouldNotSwallowExitCodeOfSibtButPassItOnToAnacron(self, fixture, 
      capfd):
    fixture.scheduleWithMockedSibt(r"""#!/usr/bin/env bash
    exit 4""", [anyScheduling()])

    _, stderr = capfd.readouterr()
    assert "status: 4" in stderr

  def test_shouldCopyAnacronsBehaviorWhenPredictingTheNextExecutionTime(
      self, fixture):
    fixture.setCurrentLocalTime(BeginningOf1985)

    assert fixture.nextExecutionLocalTime(timedelta(days=2),
        datetime(2010, 1, 1, 0, 0, 0, 0)) == datetime(2010, 1, 3, 0, 0, 0, 0)

    assert fixture.nextExecutionLocalTime(timedelta(days=3, hours=5),
        datetime(2010, 1, 1, 20, 0, 0, 0), allowedHours="0-24") == \
            datetime(2010, 1, 4, 0, 0, 0, 0)

    assert fixture.nextExecutionLocalTime(timedelta(days=3),
        datetime(2010, 1, 1, 20, 0, 0, 0),
        allowedHours="5-13") == datetime(2010, 1, 4, 5, 0, 0, 0)

  def test_shouldNotReturnATimeInThePastAsNextExecutionTime(self, fixture):
    now = BeginningOf1985
    fixture.setCurrentLocalTime(now)

    assert fixture.nextExecutionLocalTime(AnyInterval, 
        now - timedelta(days=300), 
        allowedHours="5-13") == now + timedelta(hours=5)

    fixture.setCurrentLocalTime(now + timedelta(hours=6, minutes=12))
    assert fixture.nextExecutionLocalTime(AnyInterval, 
        now - timedelta(days=300), 
        allowedHours="5-13") == now + timedelta(hours=6, minutes=12)

    fixture.setCurrentLocalTime(now + timedelta(hours=13, minutes=1))
    assert fixture.nextExecutionLocalTime(AnyInterval, 
        now - timedelta(days=300), 
        allowedHours="5-13") == now + timedelta(days=1, hours=5)

    fixture.setCurrentLocalTime(now)
    assert fixture.nextExecutionLocalTime(AnyInterval, None,
        allowedHours="1-24") == now + timedelta(hours=1)

  def test_shouldHaveAnInterfaceToAnacronsStartHoursRange(self, fixture):
    assert "AllowedHours" in fixture.optionNames

    fixture.init()

    def checkTab(tabPath):
      strToTest(local(tabPath).read()).shouldIncludeLinePatterns(
          "*START_HOURS_RANGE=6-20")
      return True
    schedulings = [buildScheduling(AllowedHours="6-20")]
    fixture.checkOption("-t", schedulings, checkTab)

  def test_shouldCheckIfAllowedHoursSettingHasTheRightSyntax(self, fixture):
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

  def test_shouldReturnAsManyCheckErrorsAsItCanFind(self, fixture):
    fixture.init()

    schedulings = [
        buildScheduling(AllowedHours="bar"),
        buildScheduling(AllowedHours="3")]

    assert len(fixture.check(schedulings)) > 1

  def test_shouldManageToBeInitializedMultipleTimesWithTheSameFolders(
      self, fixture):
    fixture.init()
    fixture.init()
