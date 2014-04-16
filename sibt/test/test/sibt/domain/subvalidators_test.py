import pytest
import os.path
from sibt.domain.subvalidators import LocExistenceValidator, \
    LocAbsoluteValidator, LocNotEmptyValidator

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

def mockRule(loc1, loc2, name=None):
  ret = lambda x:x
  ret.loc = lambda x: str(loc1) if x == 1 else str(loc2)
  ret.name = name or str(hash(loc2))

  return ret

def validRule(fix):
  return mockRule(fix.validLocDir(), fix.validLocDir())

class ValidatorTest(object):
  def test_validatorShouldReturnNoErrorsIfRulesAreOk(self, fix):
    validator = self.construct()
    rules = [validRule(fix), validRule(fix)]
    assert validator.validate(rules) == []

class Test_LocExistenceValidatorTest(ValidatorTest):
  def construct(self):
    return LocExistenceValidator()

  def test_shouldCheckIfLocsAreFolders(self, fix):
    validator = self.construct()
    aFile = fix.tmpdir.join("file")
    aFile.write("")
    assert "is file" in validator.validate([mockRule(
        aFile,
        fix.validLocDir())])[0]

    errors = validator.validate([validRule(fix),
        mockRule(fix.validLocDir(), "/does/not/exist", name="rulename")])
    assert len(errors) == 1
    assert "does not exist" in errors[0]
    assert "rulename" in errors[0]

    assert len(validator.validate([mockRule("", fix.validLocDir())])) == 1

class Test_LocAbsoluteValidatorTest(ValidatorTest):
  def construct(self):
    return LocAbsoluteValidator()

  def test_shouldReturnErrorsIfALocIsRelativeEvenIfItExists(self, fix):
    validator = self.construct()

    relativePath = os.path.relpath(str(fix.tmpdir))
    assert "not absolute" in validator.validate([mockRule(fix.validLocDir(),
        relativePath)])[0]

class Test_LocNotEmptyValidatorTest(ValidatorTest):
  def construct(self):
    return LocNotEmptyValidator()

  def test_shouldComplainIfALocIsAnEmptyDirectory(self, fix):
    validator = self.construct()

    assert "is empty" in validator.validate([validRule(fix), mockRule(
        fix.validLocDir(), fix.tmpdir.mkdir("empty-dir"))])[0]
        

