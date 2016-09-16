import pytest
from sibt.infrastructure.filesdbschedulingslog import FilesDBSchedulingsLog
from test.common.builders import schedulingLogging, anyUTCDateTime, \
    constantTimeClock
from test.common.assertutil import iterToTest, strToTest
from datetime import datetime, timezone
from sibt.domain.schedulinglogging import SchedulingResult
from test.common.presetcyclingclock import PresetCyclingClock
from test.sibt.infrastructure.linebufferedloggertest import \
    LineBufferedLoggerTest

SpecialRuleName = "lenore"

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.log = FilesDBSchedulingsLog(str(tmpdir))

  def addFinishedLogging(self, ruleName, scheduling):
    def writeOutput(outputFile):
      outputFile.write(scheduling.output.encode())
      return scheduling.succeeded

    clock = PresetCyclingClock(scheduling.startTime, scheduling.endTime)
    self.log.addLogging(ruleName, clock, writeOutput)

  def loggingsOf(self, ruleName):
    return self.log.loggingsOfRules([ruleName])[ruleName]

  def callWithLoggerAndClose(self, func):
    def execute(logger):
      func(logger)
      return True
    self.log.addLogging(SpecialRuleName, constantTimeClock(), execute)

  def readLines(self):
    logging = self.loggingsOf(SpecialRuleName)[0]
    return logging.output.splitlines()

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_FilesDBSchedulingsLogTest(LineBufferedLoggerTest):
  def test_shouldReturnAnEmptyListForAnyRuleNameIfNothingWasWritten(self, 
      fixture):
    assert fixture.log.loggingsOfRules(["foo", "bar"]) == dict(foo=[], bar=[])

  def test_shouldReturnLoggingsForARuleInTheOrderTheyWereAdded(self, fixture):
    logging1 = schedulingLogging(
        startTime=datetime(2003, 3, 24, 10, 55, 0, 0, timezone.utc))
    logging2 = schedulingLogging()

    fixture.addFinishedLogging("foo", logging1)
    fixture.addFinishedLogging("foo", logging2)

    assert fixture.log.loggingsOfRules(["foo", "bar"]) == dict(
        foo=[logging1, logging2], bar=[])

  def test_shouldCorrectlyReadSchedulingsThatAreStillInProgress(self, fixture):
    startTime = anyUTCDateTime()
    quuxLoggings = []

    def executeScheduling(logger):
      logger.write(b"output\n")
      quuxLoggings.extend(fixture.loggingsOf("quux"))
      return True

    fixture.log.addLogging("quux", constantTimeClock(startTime), 
        executeScheduling)

    iterToTest(quuxLoggings).shouldContainMatching(
        lambda logging: 
          logging.startTime == startTime and
          logging.output == "output\n" and
          logging.finished is False)

  def test_shouldNotWriteAnythingWhenReadingLoggings(self, fixture):
    fixture.tmpdir.chmod(0o500)

    fixture.log.loggingsOfRules(["foo"])

  def test_shouldLogAndRethrowExceptions(self, fixture):
    class TestException(Exception):
      def __str__(self):
        return "we have a problem"

    def raiseException(logFile):
      raise TestException()

    with pytest.raises(TestException):
      fixture.log.addLogging("foo", constantTimeClock(), raiseException)
    
    iterToTest(fixture.loggingsOf("foo")).shouldContainMatching(
        lambda logging:
          "internal" in logging.output and
          "exception" in logging.output and
          "we have a problem" in logging.output and
          not logging.succeeded)
  
  def test_shouldLogSystemExceptionsInLessDetail(self, fixture):
    class SysException(BaseException):
      pass

    def raiseException(logger):
      raise SysException()

    with pytest.raises(SysException):
      fixture.log.addLogging("foo", constantTimeClock(), raiseException)

    iterToTest(fixture.loggingsOf("foo")).shouldContainMatching(
        lambda logging: strToTest(logging.output).shouldInclude("exception").\
            but.shouldNotInclude("traceback"))
