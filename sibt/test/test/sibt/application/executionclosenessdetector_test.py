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

from sibt.application.executionclosenessdetector import \
    ExecutionClosenessDetector
from test.common.builders import constantTimeClock, anyUTCDateTime, execution, \
    mockRule
from datetime import timedelta, datetime, timezone
from test.common import mock

def make(minimum=timedelta(hours=1), currentTime=anyUTCDateTime()):
  return ExecutionClosenessDetector(constantTimeClock(currentTime), minimum)

def test_shouldConsiderItStableIfThereIsNoNextExecution():
  detector = make()
  rule = mockRule(nextExecution=None)
  assert detector.isInUnstablePhase(rule) is False

def test_shouldConsiderItUnstableIfTheRuleIsExecuting():
  detector = make()
  rule = mockRule(nextExecution=None, executing=True)
  assert detector.isInUnstablePhase(rule) is True

def test_shouldDetectClosenessAlsoIfTheNextExecutionIsInThePast():
  minimum = timedelta(minutes=45)
  nextTime = datetime(2004, 1, 1, 0, 0, 0, 0, timezone.utc)
  tooClose = datetime(2004, 1, 1, 0, 44, 59, 0, timezone.utc)
  nextIsLongAgoNow = datetime(2004, 1, 1, 0, 46, 0, 0, timezone.utc)

  rule = mockRule(nextExecution=execution(startTime=nextTime))

  assert make(minimum=minimum, currentTime=tooClose).isInUnstablePhase(
      rule) is True
  assert make(minimum=minimum, currentTime=nextIsLongAgoNow).isInUnstablePhase(
      rule) is False
