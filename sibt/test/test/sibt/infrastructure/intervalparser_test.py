import pytest
from sibt.infrastructure.intervalparser import IntervalParser

class Fixture(object):
  def __init__(self):
    self.parser = IntervalParser()

  def parse(self, string):
    return self.parser.parseNumberOfDays(string)

  def checkResult(self, string, expectedResult):
    assert self.parse(string) == expectedResult

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldParseSingleNumberOrDaysSuffixAsNumberOfDaysIgnoringWhitespace(
    fixture):
  fixture.checkResult("2", 2)
  fixture.checkResult("  25 ", 25)
  fixture.checkResult(" 1 2 3 ", 123)
  fixture.checkResult(" 8 days", 8)

def test_shouldInterpretWeeksSuffixAsMultiplier7(fixture):
  fixture.checkResult("5weeks", 35)
  fixture.checkResult("2 weeks ", 14)

def test_shouldAcceptAnySubstringFromTheBeginningOfSuffixes(fixture):
  fixture.checkResult("10 we", 70)
  fixture.checkResult(" 3 d", 3)

def test_shouldThrowExceptionIfUnknownSuffixIsUsed(fixture):
  with pytest.raises(Exception):
    fixture.parse("2n")
  with pytest.raises(Exception):
    fixture.parse("2wa")

def test_shouldThrowExceptionIfZeroOrLessDaysAreDenoted(fixture):
  with pytest.raises(Exception):
    fixture.parse("0")
  with pytest.raises(Exception):
    fixture.parse("-3 weeks")

