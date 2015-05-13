import os.path
from sibt.domain.subvalidators import LocExistenceValidator, \
    LocNotEmptyValidator, NoOverlappingWritesValidator, \
    NoSourceDirOverwriteValidator, SchedulerCheckValidator
from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockRuleSet
from test.common.assertutil import iterToTest, strToTest
from sibt.domain.syncrule import LocCheckLevel

class Test_SchedulerCheckValidatorTest(ValidatorTest):
  def construct(self):
    return SchedulerCheckValidator()

  def test_shouldMakeEachSchedulerErrorIntoAString(self, fix):
    validator = self.construct()

    ruleSet = mockRuleSet([], schedulerErrors=[("sched1", "foo"), 
      ("sched2", "bar")])

    iterToTest(validator.validate(ruleSet)).shouldIncludeMatching(
        lambda error: "sched1" in error and "reported error" in error and \
            "foo" in error,
        lambda error: "sched2" in error and "bar" in error)

class Test_LocExistenceValidatorTest(ValidatorTest):
  def construct(self):
    return LocExistenceValidator()

  def invalidRule(self, fix, ruleName, options=None):
    return fix.mockRule(fix.validLocDir(), "/does/not/exist", name=ruleName,
        options=options)

  def test_shouldSeeItAsAnErrorIfALocIsAFile(self, fix):
    validator = self.construct()
    aFile = fix.tmpdir.join("file")
    aFile.write("")
    assert "is file" in validator.validate([fix.mockRule(
        aFile,
        fix.validLocDir())])[0]

  def test_shouldReportErrorIfALocDoesNotExistAsADirectory(self, fix):
    validator = self.construct()
    ruleName = "rulename"
    iterToTest(validator.validate([fix.validRule(), self.invalidRule(fix, 
      ruleName)])).shouldContainMatching(lambda error: 
          "does not exist" in error and 
          ruleName in error)

  def test_shouldIgnoreErrorsIfCheckLevelIsNone(self, fix):
    validator = self.construct()
    assert validator.validate([self.invalidRule(fix, "foo", 
      options={ "LocCheckLevel": LocCheckLevel.None_ })]) == []

class Test_LocNotEmptyValidatorTest(ValidatorTest):
  def construct(self):
    return LocNotEmptyValidator()

  def test_shouldComplainIfALocIsAnEmptyDirectoryAndIfTheCheckLevelIsStrict(
      self, fix):
    validator = self.construct()
    emptyDir = fix.tmpdir.mkdir("empty-dir")

    def invalidRule(locCheckLevel):
      return fix.mockRule(fix.validLocDir(), emptyDir,
          options={"LocCheckLevel": locCheckLevel})

    assert "is empty" in validator.validate([fix.validRule(), 
      invalidRule(LocCheckLevel.Strict)])[0]

    assert len(validator.validate([invalidRule(LocCheckLevel.Default)])) == 0
    assert len(validator.validate([invalidRule(LocCheckLevel.None_)])) == 0

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

    strToTest(validator.validate([fix.validRule(), 
      fix.mockRule("/mnt/data/foo", "/mnt/data")])[0]).shouldIncludeInOrder(
          "foo", "within",  "/mnt")

    assert len(validator.validate([fix.mockRule("/src", "/src")])) > 0

    assert len(validator.validate([fix.mockRule("/", "/mnt/backup")])) == 0
