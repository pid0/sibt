from sibt.application.executionclosenessdetector import \
    ExecutionClosenessDetector
from test.common.builders import constantTimeClock, anyUTCDateTime, execution
from datetime import timedelta, datetime, timezone
from test.common import mock

def make(minimum=timedelta(hours=1), currentTime=anyUTCDateTime()):
  return ExecutionClosenessDetector(constantTimeClock(currentTime), minimum)

def mockRule(nextExecution=None, executing=False, latestExecution=None):
  ret = mock.mock()
  ret.nextExecution = nextExecution
  ret.latestExecution = latestExecution
  ret.executing = executing
  return ret

def test_shouldConsiderItStableIfThereIsNoNextExecution():
  detector = make()
  rule = mockRule(nextExecution=None)
  assert detector.isInUnstablePhase(rule) is False

def test_shouldConsiderItUnstableIfTheRuleIsExecuting():
  detector = make()
  rule = mockRule(nextExecution=None, executing=True)
  assert detector.isInUnstablePhase(rule) is True

def test_shouldDetectClosenessAlsoIfTheNextExecutionIsInThePast():
  minimum = timedelta(minutes=45)
  nextTime = datetime(2004, 1, 1, 0, 0, 0, 0, timezone.utc)
  tooClose = datetime(2004, 1, 1, 0, 44, 59, 0, timezone.utc)
  nextIsLongAgoNow = datetime(2004, 1, 1, 0, 46, 0, 0, timezone.utc)

  rule = mockRule(nextExecution=execution(startTime=nextTime))

  assert make(minimum=minimum, currentTime=tooClose).isInUnstablePhase(
      rule) is True
  assert make(minimum=minimum, currentTime=nextIsLongAgoNow).isInUnstablePhase(
      rule) is False
