import pytest
from sibt.domain.queuingscheduler import QueuingScheduler
from test.common import mock
from test.common.builders import anyScheduling

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

  queuing = QueuingScheduler(sub)
  assert queuing.foo(1, 2) == 3

  sub.checkExpectedCalls()

def test_shouldStoreArgsToRunOrCheckAndForwardThemWhenExecuteOrCheckAllIsCalled(
    fixture):
  sub = mock.mock()
  expectedSchedulings = [anyScheduling(), anyScheduling(), anyScheduling()]
  checkedSchedulings = [anyScheduling(), anyScheduling()]

  queuing = QueuingScheduler(sub)

  queuing.run(expectedSchedulings[0:1])
  queuing.run(expectedSchedulings[1:3])

  queuing.check(checkedSchedulings[0:1])
  queuing.check(checkedSchedulings[1:2])

  sub.expectCallsInOrder(mock.callMatching("run", lambda schedulings:
      schedulings == expectedSchedulings), mock.callMatching("check", 
      lambda schedulings: schedulings == checkedSchedulings, ret=["abc"]))

  queuing.executeSchedulings()
  errors = queuing.checkAll()
  assert len(errors) == 1
  assert "abc" in errors[0]
  assert checkedSchedulings[0].ruleName in errors[0]
  assert checkedSchedulings[1].ruleName in errors[0]

  sub.checkExpectedCalls()

def test_shouldNotCallSubSchedulerIfNoSchedulingsWereQueued(fixture):
  sub = mock.mock()
  queuing = QueuingScheduler(sub)

  queuing.executeSchedulings()
      

  
