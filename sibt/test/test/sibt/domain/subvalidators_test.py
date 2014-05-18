import os.path
from sibt.domain.subvalidators import LocExistenceValidator, \
    LocAbsoluteValidator, LocNotEmptyValidator, NoOverlappingWritesValidator, \
    NoSourceDirOverwriteValidator
from test.common.validatortest import fix, mockRule, validRule, ValidatorTest

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

    ruleName = "rulename"
    errors = validator.validate([validRule(fix),
        mockRule(fix.validLocDir(), "/does/not/exist", name=ruleName)])
    assert len(errors) == 1
    assert "does not exist" in errors[0]
    assert ruleName in errors[0]

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

class Test_NoOverlappingWritesValidator(ValidatorTest):
  def construct(self):
    return NoOverlappingWritesValidator()
        
  def test_shouldReturnAnErrorIfTheLocARuleWritesToIsWithinThatOfASecond(
      self, fix):
    validator = self.construct()
    assert "overlapping" in validator.validate([
        mockRule("/src/1", "/dest/1"),
        mockRule("/src/2", "/dest/1/foo")])[0]
    assert len(validator.validate([
        mockRule("/src/1", "/dest/1"),
        mockRule("/dest/1", "/dest/2", writeLocs=[1,2])])) == 1

class Test_NoSourceDirOverwriteValidator(ValidatorTest):
  def construct(self):
    return NoSourceDirOverwriteValidator()

  def test_shouldFindAnErrorInAWriteLocThatContainsANonWriteLoc(self, fix):
    validator = self.construct()

    assert "foo within /mnt" in validator.validate([validRule(fix),
      mockRule("/mnt/data/foo", "/mnt/data")])[0]

    assert len(validator.validate([mockRule("/src", "/src")])) > 0
