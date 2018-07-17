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

from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode

class Execution(CaseClassEqualityHashCode):
  def __init__(self, startTime, output, result):
    self.startTime = startTime
    self.output = output
    self._result = result
    self.finished = result is not None

    if self.finished:
      self.endTime = result.endTime
      self.succeeded = result.succeeded
  
  def __repr__(self):
    return "Execution{0}".format((self.startTime, self.output, self._result))

class ExecutionResult(CaseClassEqualityHashCode):
  def __init__(self, endTime, succeeded):
    self.endTime = endTime
    self.succeeded = succeeded
  
  def __repr__(self):
    return "ExecutionResult{0}".format((self.endTime, self.succeeded))
