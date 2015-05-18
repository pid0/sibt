import pytest
from test.common.builders import mockRuleSet, mockRule

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
    self.nameCounter += 1
    return mockRule(loc1=loc1, loc2=loc2, 
        name=name or "rule-" + str(self.nameCounter),
        **kwargs)

  def validRule(self):
    return self.mockRule(self.validLocDir(), self.validLocDir())

@pytest.fixture
def fix(tmpdir):
  return Fixture(tmpdir)

class ValidatorTest(object):
  def test_validatorShouldReturnNoErrorsIfTheRulesAreOk(self, fix):
    validator = self.construct()
    ruleSet = mockRuleSet([fix.validRule(), fix.validRule()],
        schedulerErrors=[])
    assert validator.validate(ruleSet) == []
