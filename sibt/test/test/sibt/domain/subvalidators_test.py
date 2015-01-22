import os.path
from sibt.domain.subvalidators import LocExistenceValidator, \
    LocAbsoluteValidator, LocNotEmptyValidator, NoOverlappingWritesValidator, \
    NoSourceDirOverwriteValidator, SchedulerCheckValidator
from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockRuleSet
from test.common.assertutil import iterableContainsInAnyOrder

class Test_SchedulerCheckValidatorTest(ValidatorTest):
  def construct(self):
    return SchedulerCheckValidator()

  def test_shouldMakeEachSchedulerErrorIntoAString(self, fix):
    validator = self.construct()

    ruleSet = mockRuleSet([], schedulerErrors=[("sched1", "foo"), 
      ("sched2", "bar")])

    assert iterableContainsInAnyOrder(validator.validate(ruleSet),
        lambda error: "sched1" in error and "reported error" in error and \
            "foo" in error,
        lambda error: "sched2" in error and "bar" in error)

class Test_LocExistenceValidatorTest(ValidatorTest):
  def construct(self):
    return LocExistenceValidator()

  def test_shouldCheckIfLocsAreFolders(self, fix):
    validator = self.construct()
    aFile = fix.tmpdir.join("file")
    aFile.write("")
    assert "is file" in validator.validate([fix.mockRule(
        aFile,
        fix.validLocDir())])[0]

    ruleName = "rulename"
    errors = validator.validate([fix.validRule(),
        fix.mockRule(fix.validLocDir(), "/does/not/exist", name=ruleName)])
    assert len(errors) == 1
    assert "does not exist" in errors[0]
    assert ruleName in errors[0]

    assert len(validator.validate([fix.mockRule("", fix.validLocDir())])) == 1

class Test_LocAbsoluteValidatorTest(ValidatorTest):
  def construct(self):
    return LocAbsoluteValidator()

  def test_shouldReturnErrorsIfALocIsRelativeEvenIfItExists(self, fix):
    validator = self.construct()

    relativePath = os.path.relpath(str(fix.tmpdir))
    assert "not absolute" in validator.validate([fix.mockRule(fix.validLocDir(),
        relativePath)])[0]

class Test_LocNotEmptyValidatorTest(ValidatorTest):
  def construct(self):
    return LocNotEmptyValidator()

  def test_shouldComplainIfALocIsAnEmptyDirectory(self, fix):
    validator = self.construct()

    assert "is empty" in validator.validate([fix.validRule(), fix.mockRule(
        fix.validLocDir(), fix.tmpdir.mkdir("empty-dir"))])[0]

class Test_NoOverlappingWritesValidator(ValidatorTest):
  def construct(self):
    return NoOverlappingWritesValidator()
        
  def test_shouldReturnAnErrorIfTheLocARuleWritesToIsWithinThatOfASecond(
      self, fix):
    validator = self.construct()
    assert "overlapping" in validator.validate([
        fix.mockRule("/src/1", "/dest/1"),
        fix.mockRule("/src/2", "/dest/1/foo")])[0]
    assert len(validator.validate([
        fix.mockRule("/src/1", "/dest/1"),
        fix.mockRule("/dest/1", "/dest/2", writeLocs=[1,2])])) == 1

class Test_NoSourceDirOverwriteValidator(ValidatorTest):
  def construct(self):
    return NoSourceDirOverwriteValidator()

  def test_shouldFindAnErrorInAWriteLocThatContainsANonWriteLoc(self, fix):
    validator = self.construct()

    assert "foo within /mnt" in validator.validate([fix.validRule(),
      fix.mockRule("/mnt/data/foo", "/mnt/data")])[0]

    assert len(validator.validate([fix.mockRule("/src", "/src")])) > 0
