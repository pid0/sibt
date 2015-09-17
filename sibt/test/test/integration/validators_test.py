from test.common.validatortest import fix, ValidatorTest
from test.common.builders import ruleSet
from sibt.domain import constructRulesValidator

class Test_ValidatorCollectionTest(ValidatorTest):
  def construct(self):
    return constructRulesValidator()

  def test_shouldReturnAnErrorIfLoc1EqualsLoc2(self, fix):
    validator = self.construct()

    locDir = fix.validLocDir()
    assert len(validator.validate(ruleSet(
      fix.mockRule(locDir, locDir)))) > 0
