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
from sibt.infrastructure.displaystring import DisplayString

def test_shouldBeAbleToDetermineItsTerminalDisplayWidth():
  assert len(DisplayString("ab")) == 2
  assert len(DisplayString("aＢ")) == 3
  assert len(DisplayString("a形")) == 3
  assert len(DisplayString("a\u0306b")) == 2

def test_shouldBeAbleToSliceWithGlyphBoundaries():
  string = DisplayString("aＢc")
  assert string.partition(0) == (DisplayString(""), DisplayString("aＢc"))
  assert string.partition(1) == (DisplayString("a"), DisplayString("Ｂc"))
  assert string.partition(2) == (DisplayString("a"), DisplayString("Ｂc"))
  assert string.partition(3) == (DisplayString("aＢ"), DisplayString("c"))
  assert string.partition(4) == (DisplayString("aＢc"), DisplayString(""))
  assert string.partition(10) == (DisplayString("aＢc"), DisplayString(""))

def test_shouldHaveAStringLikeIndexMethod():
  string = DisplayString("aＢc")
  assert string.index("c") == 3
  assert string.index("Ｂc") == 1
  with pytest.raises(ValueError):
    string.index("d")
