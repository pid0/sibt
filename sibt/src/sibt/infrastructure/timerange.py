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

from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode
from datetime import time

class TimeRange(CaseClassEqualityHashCode):
  def __init__(self, inclusiveStart, inclusiveEnd):
    self.start = inclusiveStart
    self.end = inclusiveEnd
    
  def __contains__(self, other):
    if self.start > self.end:
      return not (other > self.end and other < self.start)
    return other >= self.start and other <= self.end
    
  def __repr__(self):
    return "TimeRange{0}".format((self.start, self.end))

def fullTimeRange():
  return TimeRange(time.min, time.max)
def timeRange(start, end):
  return TimeRange(start, end)
