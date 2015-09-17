import os.path
from sibt.domain.subvalidators import LocExistenceValidator, \
    LocNotEmptyValidator, NoOverlappingWritesValidator, \
    NoSourceDirOverwriteValidator, SchedulerCheckValidator, \
    AllSharedOptsEqualValidator
from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockSched, optInfo, mockRule, ruleSet
from test.common.assertutil import iterToTest, strToTest
from sibt.domain.syncrule import LocCheckLevel
from test.common import mock

#refactor this shit
def schedCallWithRules(action, *rules, **kwargs):
  return mock.callMatching(action, lambda schedulings:
      set(schedulings) == set(rule.scheduling for rule in rules),
      **kwargs)

class Test_SchedulerCheckValidatorTest(ValidatorTest):
  def construct(self):
    return SchedulerCheckValidator()

  def test_shouldTurnEachCheckErrorFromTheUsedSchedulersIntoAString(self, fix):
    sched1, sched2 = mockSched("first"), mockSched("second")
    rule1, rule2 = mockRule(scheduler=sched1), mockRule(scheduler=sched2)
    validator = self.construct()

    sched1.expectCalls(schedCallWithRules("check", rule1, ret=["foo", "bar"]))
    sched2.expectCalls(schedCallWithRules("check", rule2, ret=["quux"]))

    iterToTest(validator.validate(ruleSet(rule1, rule2))).shouldIncludeMatching(
        lambda error: "first" in error and "reported error" in error and \
            "foo" in error,
        lambda error: "first" in error and "bar" in error,
        lambda error: "second" in error and "quux" in error)

class Test_AllSharedOptsEqualValidatorTest(ValidatorTest): 
  def construct(self):
    return AllSharedOptsEqualValidator()

  def test_shouldCheckIfAllSharedOptionValuesOfAllRulesOfASchedulerAreEqual(
      self, fix):
    schedName = "sched-with-shared-opts"
    sched = mockSched(schedName, sharedOptions=[optInfo("ConfDir"), 
      optInfo("DestFile"), optInfo("Version")])
    def rule(**schedOpts):
      return mockRule(scheduler=sched, schedOpts=schedOpts)

    rules = [
      rule(Version="1", ConfDir="/home", DestFile="/etc/foo"),
      rule(Version="1", ConfDir="/etc", DestFile="/etc/foo"),
      rule(Version="1", ConfDir="/usr/share")]

    validator = self.construct()

    iterToTest(validator.validate(ruleSet(*rules))).\
        shouldContainMatchingInAnyOrder(
            lambda error: all(string in error for string in [
              "ConfDir", "/home", "/etc", "/usr/share"]),
            lambda error: all(string in error for string in [
              "DestFile", "‘/etc/foo’", "‘’"]))

  def test_shouldReturnTheErrorsOfTheFirstSchedulerThatHasSome(self, fix):
    sched = mockSched(sharedOptions=[optInfo("UseVarDir")])
    rule1, rule2 = mockRule(scheduler=sched, schedOpts=dict(UseVarDir=True)), \
        mockRule(scheduler=sched, schedOpts=dict(UseVarDir=False))
    def visitSchedulers(visitFunc):
      assert visitFunc(sched, [rule1]) == None
      ret = visitFunc(sched, [rule1, rule2])
      assert len(ret) == 1
      return ret

    ruleSet = lambda x:x
    ruleSet.visitSchedulers = visitSchedulers
    validator = self.construct()
    validator.validate(ruleSet)

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
