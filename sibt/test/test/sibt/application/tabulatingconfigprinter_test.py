from sibt.application.tabulatingconfigprinter import LastStatus
from test.sibt.application.executionclosenessdetector_test import mockRule
from test.common.builders import execution, In1985
from test.common.assertutil import strToTest
from datetime import datetime, timezone
from test.sibt.application.datetimeformatter_test import makeFormatter

class Test_LastStatusColumnTest(object):
  def test_shouldPrintTheStartTimeIfTheRuleIsExecuting(self):
    column = LastStatus(makeFormatter())
    latestExecution = execution(startTime=In1985)
    rule = mockRule(executing=True, latestExecution=latestExecution)
    strToTest(column.formatCell(rule)).shouldInclude(
        "since", "1985", "executing")

  def test_shouldReturnNoneIfThereIsNoLastExecution(self):
    column = LastStatus(None)
    assert column.formatCell(mockRule(latestExecution=None, 
      executing=False)) is None
