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
from sibt.infrastructure.parallelmapper import ParallelMapper

def test_shouldReturnMappedResultsAsAnIterable():
  mapper = ParallelMapper()
  assert list(mapper.map(lambda x: 2 * x, [1, 2, 3])) == [2, 4, 6]

def test_shouldThrowOccurredExceptionsWhenTheResultIsRetrieved():
  def mapFunc(x):
    if x == 1:
      return 12
    if x == 2:
      raise Exception("a")
    if x == 3:
      raise Exception("b")
  
  mapper = ParallelMapper()
  result = iter(mapper.map(mapFunc, [1, 2, 3]))

  assert next(result) == 12

  with pytest.raises(Exception) as ex:
    next(result)
  assert str(ex.value) == "a"

  with pytest.raises(Exception) as ex:
    next(result)
  assert str(ex.value) == "b"
