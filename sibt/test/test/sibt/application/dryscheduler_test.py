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

import pytest
from sibt.application.dryscheduler import DryScheduler
from test.common import mock
from test.common.builders import buildScheduling

class Fixture(object):
  def __init__(self):
    pass

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldForwardAnyCallsToSubScheduler(fixture):
  sub = mock.mock()
  sub.expectCallsInOrder(mock.callMatching("foo", lambda x, y: x == 1 and 
      y == 2, ret=3))

  dry = DryScheduler(sub, object())
  assert dry.foo(1, 2) == 3

  sub.checkExpectedCalls()

def test_shouldPrintLineForEachScheduledRuleButNotScheduleThem(fixture):
  sub = mock.mock()
  sub.name = "sub-sched"
  output = mock.mock()

  output.expectCallsInAnyOrder(
      mock.callMatching("println", lambda line: "first" in line and 
        "sub-sched" in line),
      mock.callMatching("println", lambda line: "second" in line))

  dry = DryScheduler(sub, output)
  dry.schedule([buildScheduling("first"), buildScheduling("second")])

  output.checkExpectedCalls()
