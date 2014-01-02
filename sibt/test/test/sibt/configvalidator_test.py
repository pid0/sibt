from test.common.configurationbuilder import anyConfig
from test.common.rulebuilder import anyRule
from sibt.configvalidator import ConfigValidator
from test.common.assertutil import iterableContainsInAnyOrder

def test_shouldYieldAnErrorForEachRuleWithoutValidBackupProgram(tmpdir):
  validator = ConfigValidator(["program1", "program2"])
  
  validConfig = anyConfig().withRules({anyRule().
    withProgram("program1").
    withExistingSourceAndDest(tmpdir)})
  
  assert len(validator.errorsIn(validConfig.build())) == 0
  
  errors = validator.errorsIn(validConfig.withRules({
    anyRule().withProgram("invalid-program").
    withTitle("Erroneous rule1").withExistingSourceAndDest(tmpdir),
    anyRule().withProgram("invalid-program2").
    withTitle("Erroneous rule2").withExistingSourceAndDest(tmpdir)}).build())
  
  assert iterableContainsInAnyOrder(errors,
    lambda error: "Unknown backup program" in error and 
      "Erroneous rule1" in error,
    lambda error: "Unknown" in error and "rule2" in error)
  
def test_shouldYieldAnErrorForEachRuleWhoseSourceDoesntExist(tmpdir):
  validator = ConfigValidator(["sync"])
  errors = validator.errorsIn(anyConfig().withRules({
    anyRule().withProgram("sync").withSource("/some/folder").
    withDest(str(tmpdir))}).build())
  assert len(errors) == 1
  assert ("Source" in errors[0] and
    "not exist" in errors[0] and
    "/some/folder" in errors[0])
  
def test_shouldConsiderADestinationFaultyIffItsParentDoesNotExist(
  tmpdir):
  validator = ConfigValidator(["sync"])
  
  validDestinationButEndingWithSlash = str(tmpdir.join(
    "ends-with-slash")) + "/"
    
  errors = validator.errorsIn(anyConfig().withRules({
    anyRule().withProgram("sync").
    withExistingSourceAndDest(tmpdir).
    withDest(validDestinationButEndingWithSlash),
    
    anyRule().withProgram("sync").withTitle("non-existent-parent").
    withExistingSourceAndDest(tmpdir).
    withDest(str(tmpdir.join("parentOfDestination").join("folder")))}).build())
  
  assert iterableContainsInAnyOrder(errors,
    lambda error: "non-existent-parent" in error and 
      "parentOfDestination" in error and
      "Parent of " in error)
  
  
def test_shouldNotAllowRelativeDirNames(tmpdir):
  validator = ConfigValidator(["sync"])
  
  errors = validator.errorsIn(anyConfig().withRules({
    anyRule().withExistingAndRelativeSourceAndDest(tmpdir).
    withProgram("sync")}).build())
  
  assert iterableContainsInAnyOrder(errors,
    lambda error: "Source of" in error and "relative" in error,
    lambda error: "Destination of" in error and "relative" in error)