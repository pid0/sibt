import pytest
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.domain.rulefactory import RuleFactory
from test.common import mock
from test.common.builders import fakeConfigurable, port

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

def test_shouldThrowExceptionIfSynchronizerOrSchedulerDoesNotExist(fixture):
  existingScheduler = fakeConfigurable("the-sched")
  existingSynchronizer = fakeConfigurable("the-syncer", ports=[])

  factory = RuleFactory([existingScheduler], [existingSynchronizer])
  with pytest.raises(ConfigConsistencyException):
    factory.build("name", {"Name": "no"}, {"Name": "the-syncer"}, False)
  with pytest.raises(ConfigConsistencyException):
    factory.build("name", {"Name": "the-sched"}, {"Name": "no"}, False)

  with outRaises():
    factory.build("works", {"Name": "the-sched"}, {"Name": "the-syncer"}, False)

def test_shouldThrowExceptionIfAnOptionIsNotSupported(fixture):
  scheduler = fakeConfigurable("sched", availableOptions=["sched-supported"])
  synchronizer = fakeConfigurable("syncer", ports=[],
      availableOptions=["syncer-supported"])

  factory = RuleFactory([scheduler], [synchronizer])

  def callBuild(schedulerOptions, synchronizerOptions):
    schedulerOptions["Name"] = "sched"
    synchronizerOptions["Name"] = "syncer"
    factory.build("rule", schedulerOptions, synchronizerOptions, True)

  with pytest.raises(ConfigConsistencyException):
    callBuild({"sched-supported": 1}, {"not": 1})
  with pytest.raises(ConfigConsistencyException):
    callBuild({"not": 1}, {"syncer-supported": 1})

  with outRaises():
    callBuild({"sched-supported": 1}, {"syncer-supported": 1})

#TODO Name is not an option when rulefactory gets passed real syncer/scheds
#TODO locations must be true locations
def test_shouldTreatLocsCorrespondingToPortsAndNameAsMinimumOptions(fixture):
  scheduler = fakeConfigurable("scheduler")
  synchronizer = fakeConfigurable("synchronizer",
      ports=[port(), port(), port(), port()])

  factory = RuleFactory([scheduler], [synchronizer])
  with pytest.raises(ConfigConsistencyException):
    factory.build("rule name", {"Name": "scheduler"}, {"Name": "synchronizer",
      "Loc1": "/some-place", "Loc2": "/foo", "Loc3": "/bar"}, True)

  with pytest.raises(ConfigConsistencyException):
    factory.build("rule", {}, {"Name": "synchronizer",
      "Loc1": "/some-place", "Loc2": "/place", "Loc3": "/bar"}, True)

  with outRaises():
    factory.build("rule", {"Name": "scheduler"}, {"Name": "synchronizer",
      "Loc1": "/some-place", "Loc2": "/place", "Loc3": "/bar",
      "Loc4": "/fourth"}, True)
