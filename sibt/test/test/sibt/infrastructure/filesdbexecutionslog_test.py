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
from sibt.infrastructure.filesdbexecutionslog import FilesDBExecutionsLog
from test.common.builders import execution, anyUTCDateTime, constantTimeClock
from test.common.assertutil import iterToTest, strToTest
from datetime import datetime, timezone
from test.common.presetcyclingclock import PresetCyclingClock
from test.sibt.infrastructure.linebufferedloggertest import \
    LineBufferedLoggerTest
from test.common.interprocesstestfixture import InterProcessTestFixture

SpecialRuleName = "lenore"

class Fixture(InterProcessTestFixture):
  def __init__(self, tmpdir):
    super().__init__("test.sibt.infrastructure.filesdbexecutionslog_test", 
        str(tmpdir))
    self.tmpdir = tmpdir
    self.log = FilesDBExecutionsLog(str(tmpdir))

  def addFinishedExecution(self, ruleName, scheduling):
    def writeOutput(outputFile):
      outputFile.write(scheduling.output.encode())
      return scheduling.succeeded

    clock = PresetCyclingClock(scheduling.startTime, scheduling.endTime)
    self.log.logExecution(ruleName, clock, writeOutput)

  def executionsOf(self, ruleName):
    return self.log.executionsOfRules([ruleName])[ruleName]

  def callWithLoggerAndClose(self, func):
    def execute(logger):
      func(logger)
      return True
    self.log.logExecution(SpecialRuleName, constantTimeClock(), execute)

  def readLines(self):
    execution = self.executionsOf(SpecialRuleName)[0]
    return execution.output.splitlines()

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_FilesDBExecutionsLogTest(LineBufferedLoggerTest):
  def test_shouldReturnAnEmptyListForAnyRuleNameIfNothingWasWritten(self, 
      fixture):
    assert fixture.log.executionsOfRules(["foo", "bar"]) == dict(foo=[], bar=[])

  def test_shouldReturnExecutionsForARuleInTheOrderTheyWereAdded(self, fixture):
    execution1 = execution(
        startTime=datetime(2003, 3, 24, 10, 55, 0, 0, timezone.utc))
    execution2 = execution()

    fixture.addFinishedExecution("foo", execution1)
    fixture.addFinishedExecution("foo", execution2)

    assert fixture.log.executionsOfRules(["foo", "bar"]) == dict(
        foo=[execution1, execution2], bar=[])

  def test_shouldCorrectlyReadExecutionsThatAreStillInProgress(self, fixture):
    startTime = anyUTCDateTime()
    executionsInThisProcess = []
    executionsInOtherProcess = []

    def execute(logger):
      logger.write(b"output\n")
      executionsInThisProcess.extend(fixture.executionsOf("quux"))
      executionsInOtherProcess.extend(fixture.inNewProcess(r"""
        return fixture.executionsOf("quux")"""))
      return True

    fixture.log.logExecution("quux", constantTimeClock(startTime), execute)

    iterToTest(executionsInOtherProcess).shouldContainMatching(
        lambda execution: 
          execution.startTime == startTime and
          execution.output == "output\n" and
          execution.finished is False)
    iterToTest(executionsInThisProcess).shouldContainMatching(
        lambda execution: execution.finished is False)

  def test_shouldNotWriteAnythingWhenReadingExecutions(self, fixture):
    fixture.tmpdir.chmod(0o500)

    fixture.log.executionsOfRules(["foo"])

  def test_shouldLogAndRethrowExceptions(self, fixture):
    class TestException(Exception):
      def __str__(self):
        return "we have a problem"

    def raiseException(logFile):
      raise TestException()

    with pytest.raises(TestException):
      fixture.log.logExecution("foo", constantTimeClock(), raiseException)
    
    iterToTest(fixture.executionsOf("foo")).shouldContainMatching(
        lambda execution:
          "internal" in execution.output and
          "exception" in execution.output and
          "we have a problem" in execution.output and
          not execution.succeeded)
  
  def test_shouldLogSystemExceptionsInLessDetail(self, fixture):
    class SysException(BaseException):
      pass

    def raiseException(logger):
      raise SysException()

    with pytest.raises(SysException):
      fixture.log.logExecution("foo", constantTimeClock(), raiseException)

    iterToTest(fixture.executionsOf("foo")).shouldContainMatching(
        lambda execution: strToTest(execution.output).\
            shouldInclude("exception").but.shouldNotInclude("traceback"))
