import pytest
from sibt.infrastructure.tableprinter import TablePrinter, _breakText
from test.common.bufferingoutput import BufferingOutput

class Fixture(object):
  def __init__(self):
    self.reset()

  def reset(self, maxWidth=0):
    self.output = BufferingOutput()
    self.printer = TablePrinter(self.output, False, maxWidth)

  @property
  def rowsString(self):
    return self.output.string.ignoringFirstLine

class VerbatimCol(object):
  header = "Verbatim"
  def formatCell(self, value):
    return value

class ConstantCol(object):
  header = "Constant"
  def __init__(self, value):
    self.value = value

  def formatCell(self, _):
    return self.value

class VariableLengthCol(object):
  header = "VarLength"
  def formatCell(self, length):
    return "x" * length

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldPrintNothingIfNoValuesAreGiven(fixture):
  fixture.printer.print([], ConstantCol("foo"), printHeaders=False)
  fixture.output.string.shouldBeEmpty()

def test_shouldPrintALineForEachTableRow(fixture):
  fixture.printer.print(["foo", "bar"], VerbatimCol())
  fixture.rowsString.shouldContainLinePatternsInOrder("*foo*", "*bar*")

def test_shouldStartCellsOfAColumnAtTheSameHorizontalPosition(fixture):
  fixture.printer.print([1, 10],
      ConstantCol("a"), VariableLengthCol(), ConstantCol("b"))
  fixture.rowsString.shouldBeginInTheSameColumn("a")
  fixture.rowsString.shouldBeginInTheSameColumn("b")

  fixture.reset()
  fixture.printer.print(["a"], VerbatimCol(), ConstantCol("x"))
  assert fixture.rowsString.string.index("x") > len("Verbatim")

def test_shouldIgnoreMaxWidthIfTheRestrictionCantBeMet(fixture):
  fixture.reset(maxWidth=1)
  fixture.printer.print(["foo"], VerbatimCol())
  fixture.rowsString.shouldContainLinePatterns("*foo*")

def test_shouldPrintNoneValuesAsNA(fixture):
  fixture.printer.print([None], VerbatimCol())
  fixture.rowsString.shouldInclude("n/a")

def test_shouldBreakTextSoThatTheSpecifiedWidthIsNeverCrossed():
  assert _breakText("foobarquux", 3) == ["foo", "bar", "quu", "x"]
  assert _breakText("foobarquux", 20) == ["foobarquux"]
  assert _breakText("", 1) == []

def test_shouldBreakTextSoNonAlphanumericCharacterGroupsEndALine():
  assert _breakText("18:23:15", 5) == ["18:", "23:15"]
  assert _breakText("foo+-bar", 5) == ["foo+-", "bar"]
  assert _breakText("+-bar", 3) == ["+-", "bar"]
  assert _breakText("-+-+-", 3) == ["-+-", "+-"]

def test_shouldConsiderDisplayWidthNotNumberOfCodepointsWhenBreakingText():
  assert _breakText("ｆｏｏ", 3) == ["ｆ", "ｏ", "ｏ"]
  assert _breakText("ｆｏｏ", 4) == ["ｆｏ", "ｏ"]
  assert _breakText("f\u0308o\u0300\u0301\u0302\u0303\u0304o", 3) == \
      ["f\u0308o\u0300\u0301\u0302\u0303\u0304o"]

def test_shouldReplaceSpacesWithNewlinesWhenNecessaryWhenBreakingText():
  assert _breakText("foo bar", 3) == ["foo", "bar"]
