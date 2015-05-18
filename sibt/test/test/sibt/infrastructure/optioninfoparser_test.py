import pytest
from sibt.infrastructure import types
from sibt.infrastructure.optioninfoparser import OptionInfoParser
from test.common.assertutil import iterToTest
from sibt.infrastructure.exceptions import ParseException

class Fixture(object):
  def __init__(self):
    self.parser = OptionInfoParser()

@pytest.fixture
def fixture():
  return Fixture()

def shouldBeInfoWith(info, name, optType):
  assert info.name == name
  assert info.optionType == optType

def test_shouldSplitStringForTypeAndNameOfOption(fixture):
  values = [("Default", "Default", types.String),
      ("b B", "B", types.Bool), 
      ("t T", "T", types.TimeDelta), 
      ("Abc|Def|Ghi E", "E", lambda enum: iterToTest(enum.values).\
          shouldContainMatching(
            lambda val: val == "Abc",
            lambda val: val == "Def",
            lambda val: val == "Ghi")),
      ("s S", "S", types.String), 
      ("f F", "F", types.File),
      ("p P", "P", types.Positive)]

  for string, expectedName, expectedType in values:
    info = fixture.parser.parse(string)
    assert info.name == expectedName
    if callable(expectedType):
      expectedType(info.optionType)
    else:
      assert info.optionType == expectedType, string

def test_shouldThrowAnExceptionIfOptionNameContainsASpace(fixture):
  with pytest.raises(ParseException):
    fixture.parser.parse("b C D")

def test_shouldThrowAnExceptionIfTypeIsNotKnown(fixture):
  with pytest.raises(ParseException):
    fixture.parser.parse("zz Opt")

