import pytest
from test.common import mock
from test.common.builders import mockRule
from sibt.domain.rulescoordinator import RulesCoordinator
from sibt.domain.subvalidators import AcceptingValidator
from sibt.domain.exceptions import ValidationException

class Fixture(object):
  def __init__(self):
    self.counter = 0

  def ruleWithSched(self, scheduler):
    self.counter += 1
    return mockRule(name="rule-" + str(self.counter), scheduler=scheduler)

  def makeCoordinator(self, *rules):
    return RulesCoordinator(list(rules))
  def schedulerErrors(self, *rules):
    coordinator = self.makeCoordinator(*rules)
    return coordinator.schedulerErrors
  def schedule(self, *rules):
    coordinator = self.makeCoordinator(*rules)
    coordinator.schedule(AcceptingValidator())

@pytest.fixture
def fixture():
  return Fixture()

def schedCallWithRules(action, *rules, **kwargs):
  return mock.callMatching(action, lambda schedulings:
      set(schedulings) == set(rule.scheduling for rule in rules),
      **kwargs)

def mockScheds(number):
  def makeSched(i):
    name = "sched-{0}".format(i + 1)
    ret = mock.mock(name)
    ret.name = name
    return ret
  return tuple(makeSched(i) for i in range(number))

def test_shouldScheduleRulesWithACommonSchedulerTogetherInASingleOperation(
    fixture):
  sched1, sched2 = mockScheds(2)
  rule1, rule2, rule3 = fixture.ruleWithSched(sched1), \
    fixture.ruleWithSched(sched2), \
    fixture.ruleWithSched(sched1)

  sched1.expectCalls(schedCallWithRules("run", rule1, rule3))
  sched2.expectCalls(schedCallWithRules("run", rule2))

  fixture.schedule(rule1, rule2, rule3)

  sched1.checkExpectedCalls()
  sched2.checkExpectedCalls()

def test_shouldCollectCheckErrorsFromAllSchedulersTaggedWithTheSchedulerName(
    fixture):
  sched1, sched2 = mockScheds(2)
  rule1, rule2 = fixture.ruleWithSched(sched1), fixture.ruleWithSched(sched2)

  sched1.expectCalls(schedCallWithRules("check", rule1, ret=["foo", "bar"]))
  sched2.expectCalls(schedCallWithRules("check", rule2, ret=["quux"]))

  assert set(fixture.schedulerErrors(rule1, rule2)) == \
      {(sched1.name, "foo"), (sched1.name, "bar"), (sched2.name, "quux")}

def test_shouldNotScheduleAnythingAndFailIfValidationFails(fixture):
  sched1, sched2 = mockScheds(2)
  rule1, rule2 = fixture.ruleWithSched(sched1), fixture.ruleWithSched(sched2)

  coordinator = fixture.makeCoordinator(rule1, rule2)

  validator = mock.mock()
  validator.expectCalls(mock.call("validate", (coordinator,), ret=["raven"]))

  with pytest.raises(ValidationException) as ex:
    coordinator.schedule(validator)
  assert ex.value.errors == ["raven"]


