import pytest

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.dirCounter = 0

  def validLocDir(self):
    self.dirCounter = self.dirCounter + 1
    ret = self.tmpdir.mkdir("dir" + str(self.dirCounter))
    ret.join("file").write("")
    return ret

@pytest.fixture
def fix(tmpdir):
  return Fixture(tmpdir)

def mockRule(loc1, loc2, name=None, writeLocs=[2]):
  ret = lambda x:x
  ret.locs = [str(loc1), str(loc2)]
  ret.writeLocs = [str(loc1)] if 1 in writeLocs else [] + \
      [str(loc2)] if 2 in writeLocs else []
  ret.nonWriteLocs = [str(loc1)] if 1 not in writeLocs else [] + \
      [str(loc2)] if 2 not in writeLocs else []
  ret.checkScheduler = lambda *args: None
  ret.name = name or str(hash(loc2))

  return ret

def validRule(fix):
  return mockRule(fix.validLocDir(), fix.validLocDir())

class ValidatorTest(object):
  def test_validatorShouldReturnNoErrorsIfTheRulesAreOk(self, fix):
    validator = self.construct()
    rules = [validRule(fix), validRule(fix)]
    assert validator.validate(rules) == []
