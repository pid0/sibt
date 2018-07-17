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

from datetime import time
from sibt.infrastructure.timerange import TimeRange

def test_shouldContainATimeIfItIsBetweenOrEqualToItsLimits():
  timeRange = TimeRange(time(15, 23), time(19, 57))
  
  assert time(15, 23) in timeRange
  assert time(19, 57) in timeRange
  assert time(16, 15) in timeRange
  assert time(19, 58) not in timeRange
  assert time(22, 0) not in timeRange
  assert time(15, 22) not in timeRange
  
  rangeAcrossWrapPoint = TimeRange(time(18, 10), time(4, 3))
  
  assert time(18, 10) in rangeAcrossWrapPoint
  assert time(20, 0) in rangeAcrossWrapPoint
  assert time(0, 0) in rangeAcrossWrapPoint
  assert time(4, 3) in rangeAcrossWrapPoint
  assert time(6, 15) not in rangeAcrossWrapPoint
  assert time(12, 0) not in rangeAcrossWrapPoint
  assert time(18, 9) not in rangeAcrossWrapPoint
