from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockRuleSet
from sibt.domain import constructRulesValidator

class Test_CollectionValidatorTest(ValidatorTest):
  def construct(self):
    return constructRulesValidator()

  def test_shouldComplainAboutNotExistingDirIfLocIsAnEmptyString(self, fix):
    validator = self.construct()
    errors = validator.validate(mockRuleSet(
      [fix.mockRule(fix.validLocDir(), "")]))
    assert len(errors) == 1
    assert "exist" in errors[0]

  def test_shouldFirstCheckIfALocIsAbsolute(self, fix):
    validator = self.construct()
    relDir = fix.tmpdir.mkdir("dir")
    with fix.tmpdir.as_cwd():
      assert "absolute" in validator.validate(mockRuleSet([
          fix.mockRule("dir", fix.validLocDir())]))[0]

  def test_shouldReturnAnErrorIfLoc1EqualsLoc2(self, fix):
    validator = self.construct()

    locDir = fix.validLocDir()
    assert len(validator.validate(mockRuleSet(
      [fix.mockRule(locDir, locDir)]))) > 0

#TODO shouldAlwaysCheckSchedulers: constructRulesValidator(locCheckLevel=None)
