from test.common.validatortest import fix, mockRule, validRule, ValidatorTest
from sibt.application import constructRulesValidator

class Test_CollectionValidatorTest(ValidatorTest):
  def construct(self):
    return constructRulesValidator([])

  def test_shouldComplainAboutNotExistingDirIfLocIsAnEmptyString(self, fix):
    validator = self.construct()
    errors = validator.validate([mockRule(fix.validLocDir(), "")])
    assert len(errors) == 1
    assert "exist" in errors[0]

  def test_shouldFirstCheckIfALocIsAbsolute(self, fix):
    validator = self.construct()
    relDir = fix.tmpdir.mkdir("dir")
    with fix.tmpdir.as_cwd():
      assert "absolute" in validator.validate([
          mockRule("dir", fix.validLocDir())])[0]

