import pytest
from sibt.configuration.exceptions import ConfigConsistencyException, \
    RuleNameInvalidException
from sibt.domain.rulefactory import RuleFactory
from test.common import mock
from test.common.builders import fakeConfigurable, port, optInfo, \
    location as loc, mkSyncerOpts
from sibt.domain.syncrule import LocCheckLevel
from sibt.infrastructure import types
from test.common.assertutil import strToTest
from contextlib import contextmanager

class Fixture(object):
  def __init__(self):
    self.factory = RuleFactory(None)

  def buildRuleWithNoOpts(self):
    return self.factory.build("name", fakeConfigurable(), 
        fakeConfigurable(ports=[]), {}, {}, mkSyncerOpts(), False)

@pytest.fixture
def fixture():
  return Fixture()

@contextmanager
def noException():
  yield None

def test_shouldThrowExceptionIfRuleNameContainsInvalidCharacters(fixture):
  with pytest.raises(RuleNameInvalidException) as ex:
    fixture.factory.build("foo@with space", fakeConfigurable("sched"),
        fakeConfigurable("syncer", ports=[]), {}, {}, mkSyncerOpts(), False)
  assert ex.value.invalidCharacter == " "

def test_shouldThrowExceptionIfAnOptionIsNotSupported(fixture):
  scheduler = fakeConfigurable("sched", 
      availableOptions=[optInfo("sched-supported")])
  synchronizer = fakeConfigurable("syncer", ports=[],
      availableOptions=[optInfo("syncer-supported")])

  def callBuild(ruleOptions, schedulerOptions, synchronizerOptions):
    fixture.factory.build("rule", scheduler, synchronizer, ruleOptions, 
        schedulerOptions, mkSyncerOpts(**synchronizerOptions), True)

  with pytest.raises(ConfigConsistencyException):
    callBuild({}, {"sched-supported": 1}, {"not": 1})
  with pytest.raises(ConfigConsistencyException):
    callBuild({}, {"not": 1}, {"syncer-supported": 1})

  with noException():
    callBuild({}, {"sched-supported": 1}, {"syncer-supported": 1})

  with pytest.raises(ConfigConsistencyException):
    callBuild({"Blah": 2}, {"sched-supported": 1}, {"syncer-supported": 1})

def test_shouldTreatLocsCorrespondingToPortsAsMinimumOptions(fixture):
  def locOptInfo(number):
    return optInfo("Loc" + str(number), types.Location)
  sched = fakeConfigurable("scheduler")
  syncer = fakeConfigurable("synchronizer",
      ports=[port(), port(), port(), port()],
      availableOptions=[locOptInfo(1), locOptInfo(2), locOptInfo(3), 
        locOptInfo(4)])

  loc1Through3 = {"Loc1": loc("/some-place"), "Loc2": loc("/place"), 
      "Loc3": loc("/bar")}

  with pytest.raises(ConfigConsistencyException) as ex:
    fixture.factory.build("rulename", sched, syncer, {}, {}, 
        mkSyncerOpts(**loc1Through3), True)
  strToTest(str(ex.value)).shouldIncludeInOrder("not", "minimum opt").andAlso.\
      shouldInclude("Loc4")

  with noException():
    fixture.factory.build("rule", sched, syncer, {}, {}, 
        mkSyncerOpts(Loc4=loc("/fourth"), **loc1Through3), True)

def test_shouldHaveDefaultValuesForTheRuleOptions(fixture):
  rule = fixture.buildRuleWithNoOpts()
  assert rule.options["LocCheckLevel"] == LocCheckLevel.Default
  assert rule.options["AllowedForUsers"] == ""
