import pytest
from sibt.application.dryscheduler import DryScheduler
from test.common import mock
from test.common.builders import buildScheduling

class Fixture(object):
  def __init__(self):
    pass

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldForwardAnyCallsToSubScheduler(fixture):
  sub = mock.mock()
  sub.expectCallsInOrder(mock.callMatching("foo", lambda x, y: x == 1 and 
      y == 2, ret=3))

  dry = DryScheduler(sub, object())
  assert dry.foo(1, 2) == 3

  sub.checkExpectedCalls()

def test_shouldPrintLineForEachScheduledRuleButNotScheduleThem(fixture):
  sub = mock.mock()
  sub.name = "sub-sched"
  output = mock.mock()

  output.expectCallsInAnyOrder(
      mock.callMatching("println", lambda line: "first" in line and 
        "sub-sched" in line),
      mock.callMatching("println", lambda line: "second" in line))

  dry = DryScheduler(sub, output)
  dry.schedule([buildScheduling("first"), buildScheduling("second")])

  output.checkExpectedCalls()
