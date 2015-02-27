from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockRuleSet
from sibt.domain import constructRulesValidator

class Test_CollectionValidatorTest(ValidatorTest):
  def construct(self):
    return constructRulesValidator()

  def test_shouldReturnAnErrorIfLoc1EqualsLoc2(self, fix):
    validator = self.construct()

    locDir = fix.validLocDir()
    assert len(validator.validate(mockRuleSet(
      [fix.mockRule(locDir, locDir)]))) > 0

#TODO shouldAlwaysCheckSchedulers: constructRulesValidator(locCheckLevel=None)
