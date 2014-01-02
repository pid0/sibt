from test.common.rulebuilder import anyRule
from datetime import datetime, timezone
from sibt.infrastructure.executiontimefilerepo import ExecutionTimeFileRepo

def test_shouldBeAbleToPersistentlyAssociateAnExecutionTimeToARule(tmpdir):
  repo = ExecutionTimeFileRepo(str(tmpdir))
  
  executionTime = datetime(2013, 2, 13, 13, 12, tzinfo=timezone.utc)
  
  repo.setExecutionTimeFor(anyRule().withTitle("some-rule").build(), 
    executionTime)
  
  repo2 = ExecutionTimeFileRepo(str(tmpdir))
  
  assert repo2.executionTimeOf(anyRule().withTitle(
    "some-rule").build()) == executionTime
  
def test_shouldYieldNoneWhenAskedForAExecutionTimeThatHasntBeenSet(tmpdir):
  repo = ExecutionTimeFileRepo(str(tmpdir))
  assert repo.executionTimeOf(anyRule().build()) == None