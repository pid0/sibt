# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from sibt.application.tabulatingconfigprinter import LastStatus
from test.sibt.application.executionclosenessdetector_test import mockRule
from test.common.builders import execution, In1985
from test.common.assertutil import strToTest
from datetime import datetime, timezone
from test.sibt.application.datetimeformatter_test import makeFormatter

class Test_LastStatusColumnTest(object):
  def test_shouldPrintTheStartTimeIfTheRuleIsExecuting(self):
    column = LastStatus(makeFormatter())
    currentExecution = execution(startTime=In1985)
    rule = mockRule(executing=True, currentExecution=currentExecution)
    strToTest(column.formatCell(rule)).shouldInclude(
        "since", "1985", "executing")

  def test_shouldReturnNoneIfThereIsNoLastExecution(self):
    column = LastStatus(None)
    assert column.formatCell(mockRule(lastFinishedExecution=None, 
      executing=False)) is None
