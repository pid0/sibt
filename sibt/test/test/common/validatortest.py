import pytest
from test.common.builders import ruleSet, mockRule, mockSched
from test.common import mock

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.dirCounter = 0
    self.nameCounter = 0

  def validLocDir(self):
    self.dirCounter = self.dirCounter + 1
    ret = self.tmpdir.mkdir("dir" + str(self.dirCounter))
    ret.join("file").write("")
    return ret

  def mockRule(self, loc1, loc2, name=None, **kwargs):
    sched = mockSched()
    sched.check = lambda *args: []
    self.nameCounter += 1
    return mockRule(loc1=loc1, loc2=loc2, 
        name=name or "rule-" + str(self.nameCounter),
        scheduler=sched, **kwargs)

  def validRule(self):
    return self.mockRule(self.validLocDir(), self.validLocDir())

def schedCallWithRules(action, *rules, **kwargs):
  return mock.callMatching(action, lambda schedulingSet:
      set(schedulingSet) == set(rule.scheduling for rule in rules),
      **kwargs)

@pytest.fixture
def fix(tmpdir):
  return Fixture(tmpdir)

class ValidatorTest(object):
  def test_validatorShouldReturnNoErrorsIfTheRulesAreOk(self, fix):
    validator = self.construct()
    assert validator.validate(ruleSet(fix.validRule(), fix.validRule())) == []
