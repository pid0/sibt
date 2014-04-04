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

def test_shouldParseSingleNumberOrDSuffixAsNumberOfDaysIgnoringWhitespace(
    fixture):
  fixture.checkResult("2", 2)
  fixture.checkResult("  25 ", 25)
  fixture.checkResult(" 1 2 3 ", 123)
  fixture.checkResult(" 8 d", 8)

def test_shouldInterpretWSuffixAsMultiplier7(fixture):
  fixture.checkResult("5w", 35)
  fixture.checkResult("2 w ", 14)

def test_shouldThrowExceptionIfUnknownSuffixIsUsed(fixture):
  with pytest.raises(Exception):
    fixture.parse("2n")

#TODO no zero or negative value; longer suffixes
