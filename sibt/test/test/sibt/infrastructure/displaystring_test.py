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
