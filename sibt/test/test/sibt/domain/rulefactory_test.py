import pytest
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.domain.rulefactory import RuleFactory
from test.common import mock

class Fixture(object):
  def __init__(self):
    pass

@pytest.fixture
def fixture():
  return Fixture()

def outRaises():
  class Ret(object):
    def __enter__(self):
      return self
    def __exit__(self, x, y, z):
      pass
  return Ret()

def mockConfigurable(name):
  ret = lambda x:x
  ret.name = name
  ret.availableOptions = []
  return ret

def test_shouldThrowExceptionIfInterpreterOrSchedulerDoesNotExist(fixture):
  existingScheduler = mockConfigurable("one")
  existingInterpreter = mockConfigurable("two")

  factory = RuleFactory([existingScheduler], [existingInterpreter])
  with pytest.raises(ConfigConsistencyException):
    factory.build("name", {"Name": "no"}, {"Name": "two"}, False)
  with pytest.raises(ConfigConsistencyException):
    factory.build("name", {"Name": "one"}, {"Name": "no"}, False)

  with outRaises():
    factory.build("works", {"Name": "one"}, {"Name": "two"}, False)

def test_shouldThrowExceptionIfAnOptionIsNotSupported(fixture):
  options = {"sched-unsupported": "val", "supported": "val2"}

  scheduler = mock.mock()
  scheduler.availableOptions = ["sched-supported"]
  scheduler.name = "sched"

  interpreter = mock.mock()
  interpreter.availableOptions = ["inter-supported"]
  interpreter.name = "inter"

  factory = RuleFactory([scheduler], [interpreter])

  def callBuild(schedulerOptions, interpreterOptions):
    schedulerOptions["Name"] = "sched"
    interpreterOptions["Name"] = "inter"
    factory.build("rule", schedulerOptions, interpreterOptions, True)

  with pytest.raises(ConfigConsistencyException):
    callBuild({"sched-supported": 1}, {"not": 1})
  with pytest.raises(ConfigConsistencyException):
    callBuild({"not": 1}, {"inter-supported": 1})

  with outRaises():
    callBuild({"sched-supported": 1}, {"inter-supported": 1})

