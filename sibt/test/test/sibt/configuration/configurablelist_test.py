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

from sibt.configuration.configurablelist import ConfigurableList, \
    LazyConfigurable
from sibt.configuration.exceptions import ConfigurableNotFoundException

def test_shouldLoadConfigurableOnceRequestedAndReturnTheResult():
  x = [2]
  def load():
    x[0] *= 2
    return x[0]

  confList = ConfigurableList([LazyConfigurable("foo", load)])
  assert confList.getByName("foo") == 4
  assert confList.getByName("foo") == 4

def test_shouldNotFindConfigurableIfLoadFunctionReturnsNone():
  confList = ConfigurableList([LazyConfigurable("foo", lambda: None)])
  with pytest.raises(ConfigurableNotFoundException):
    confList.getByName("foo")

def test_shouldLoadAllWhenIterating():
  x = [1]
  confList = ConfigurableList([
    LazyConfigurable("foo", lambda: x[0]),
    LazyConfigurable("bar", lambda: 2)])

  assert set(confList) == { 1, 2 }
  x[0] = 5
  assert set(confList) == { 1, 2 }
