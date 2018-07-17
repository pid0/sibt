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
from test.common import mock
from test.common.builders import mockRule, mockSched, optInfo
from sibt.domain.ruleset import RuleSet
from sibt.domain.exceptions import ValidationException, RuleExecutingException
from test.common.assertutil import iterToTest
from test.common.validatortest import schedCallWithRules

class Fixture(object):
  def __init__(self):
    self.counter = 0

  def ruleWithSched(self, scheduler, **kwargs):
    self.counter += 1
    return mockRule(name="rule-" + str(self.counter), scheduler=scheduler,
        **kwargs)

  def makeRuleSet(self, *rules):
    return RuleSet(list(rules))
  def schedule(self, *rules):
    ruleSet = self.makeRuleSet(*rules)
    ruleSet.schedule(AcceptingValidator())

@pytest.fixture
def fixture():
 return Fixture()

class AcceptingValidator(object):
  def validate(self, ruleSet):
    return []

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

  sched1.expectCalls(schedCallWithRules("schedule", rule1, rule3))
  sched2.expectCalls(schedCallWithRules("schedule", rule2))

  fixture.schedule(rule1, rule2, rule3)

  sched1.checkExpectedCalls()
  sched2.checkExpectedCalls()

def test_shouldCallVisitorWithEachSchedAndItsRulesUntilNotNoneIsReturned(
    fixture):
  sched1, sched2 = mockScheds(2)
  rule1, rule2, rule3 = fixture.ruleWithSched(sched1), \
      fixture.ruleWithSched(sched1), \
      fixture.ruleWithSched(sched2)
  ruleSet = fixture.makeRuleSet(rule1, rule2, rule3)

  visited = []
  def visit(sched, rules):
    visited.append((sched, set(rules)))

  assert ruleSet.visitSchedulers(visit) is None
  iterToTest(visited).shouldContainInAnyOrder(
      (sched1, { rule1, rule2 }),
      (sched2, { rule3 }))

  assert ruleSet.visitSchedulers(lambda *args: "foo") == "foo"

def test_shouldNotScheduleAnythingAndFailIfValidationFails(fixture):
  sched1, sched2 = mockScheds(2)
  rule1, rule2 = fixture.ruleWithSched(sched1), fixture.ruleWithSched(sched2)

  ruleSet = fixture.makeRuleSet(rule1, rule2)

  validator = mock.mock()
  validator.expectCalls(mock.call("validate", (ruleSet,), ret=["raven"]))

  with pytest.raises(ValidationException) as ex:
    ruleSet.schedule(validator)
  assert ex.value.errors == ["raven"]

def test_shouldThrowExceptionIfOneRuleIsExecuting(fixture):
  sched, = mockScheds(1)
  executingRule = fixture.ruleWithSched(sched, executing=True)

  with pytest.raises(RuleExecutingException):
    fixture.schedule(executingRule)
