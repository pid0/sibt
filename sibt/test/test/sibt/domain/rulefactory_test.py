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

def fakeConfigurable(name, *availableOptions):
  ret = lambda x:x
  ret.name = name
  ret.availableOptions = list(availableOptions)
  return ret

def withLocOptions(options):
  ret = dict(options)
  ret["Loc1"] = "/some-place"
  ret["Loc2"] = "/some-other-place"
  return ret

def test_shouldThrowExceptionIfInterpreterOrSchedulerDoesNotExist(fixture):
  existingScheduler = fakeConfigurable("one")
  existingInterpreter = fakeConfigurable("two")

  factory = RuleFactory([existingScheduler], [existingInterpreter])
  with pytest.raises(ConfigConsistencyException):
    factory.build("name", {"Name": "no"}, withLocOptions({"Name": "two"}), 
        False)
  with pytest.raises(ConfigConsistencyException):
    factory.build("name", {"Name": "one"}, withLocOptions({"Name": "no"}), 
        False)

  with outRaises():
    factory.build("works", {"Name": "one"}, withLocOptions({"Name": "two"}), 
        False)

def test_shouldThrowExceptionIfAnOptionIsNotSupported(fixture):
  scheduler = fakeConfigurable("sched", "sched-supported")
  interpreter = fakeConfigurable("inter", "inter-supported")

  factory = RuleFactory([scheduler], [interpreter])

  def callBuild(schedulerOptions, interpreterOptions):
    schedulerOptions["Name"] = "sched"
    interpreterOptions["Name"] = "inter"
    factory.build("rule", schedulerOptions, withLocOptions(interpreterOptions), 
        True)

  with pytest.raises(ConfigConsistencyException):
    callBuild({"sched-supported": 1}, {"not": 1})
  with pytest.raises(ConfigConsistencyException):
    callBuild({"not": 1}, {"inter-supported": 1})

  with outRaises():
    callBuild({"sched-supported": 1}, {"inter-supported": 1})

def test_shouldThrowExceptionIfLoc1OrLoc2OptionsAreNotPresent(fixture):
  scheduler = fakeConfigurable("scheduler")
  interpreter = fakeConfigurable("interpreter")

  factory = RuleFactory([scheduler], [interpreter])
  with pytest.raises(ConfigConsistencyException):
    factory.build("rule name", {"Name": "scheduler"}, {"Name": "interpreter",
        "Loc1": "/some-place"}, True)

  with pytest.raises(ConfigConsistencyException):
    factory.build("rule", {}, {"Name": "interpreter",
        "Loc1": "/some-place", "Loc2": "/place"}, True)
