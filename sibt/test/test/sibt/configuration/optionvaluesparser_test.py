import pytest
from sibt.domain.exceptions import LocationInvalidException
from sibt.configuration.exceptions import OptionParseException
from sibt.configuration.optionvaluesparser import parseLocation, \
    OptionValuesParser
from test.common.builders import optInfo
from sibt.infrastructure import types
from datetime import timedelta
from test.common.assertutil import strToTest, iterToTest

class Fixture(object):
  def __init__(self):
    self.parser = OptionValuesParser()

@pytest.fixture
def fixture():
  return Fixture()

def parse(optInfoType, string, optName="Opt"):
  parser = OptionValuesParser()
  return parser.parseOptions([optInfo(optName, optInfoType)], 
      { optName: string })[optName]

def shouldNotParse(optInfoType, string, *expectedPhrases, typeDesc=None):
  with pytest.raises(OptionParseException) as ex:
    parse(optInfoType, string, optName="Option")

  if typeDesc is not None:
    assert ex.value.errors[0].expectedType == typeDesc
  assert ex.value.errors[0].optionName == "Option"
  assert ex.value.errors[0].stringToParse == string
  strToTest(ex.value.errors[0].message).shouldInclude(*expectedPhrases)

def test_shouldExactlyRecognizeSyntacticSugarForSSHLocations():
  loc = parseLocation("foo:/bar:quux")
  assert loc.protocol == "ssh"
  assert loc.host == "foo"
  assert loc.path == "/bar:quux"

  loc = parseLocation("yeah@host:relative/a://b/")
  assert loc.protocol == "ssh"
  assert loc.login == "yeah"
  assert loc.path == "relative/a:/b"

  loc = parseLocation("/foo:bar")
  assert loc.protocol == "file"

  loc = parseLocation("user@host-of-syntactic-sugar:")
  assert loc.protocol == "ssh"
  assert loc.path == "."

def test_shouldReturnUnknownOptionsUnchanged(fixture):
  options = {"Opt": "Abc", "Opt2": object()}
  assert fixture.parser.parseOptions([], options) == options

def test_shouldConvertStringsIntoSuitablePythonTypesBasedOnOptionInfo(fixture):
  opts = { "NoOfCopies": "23", "Comment": "foo bar  " }
  expected = { "NoOfCopies": 23, "Comment": "foo bar  " }
  assert fixture.parser.parseOptions([optInfo("NoOfCopies", types.Positive), 
        optInfo("Comment", types.String)], opts) == expected

  assert parse(types.Positive, " 35 ") == 35

  assert parse(types.Bool, " YeS") == True
  assert parse(types.Bool, "FaLse ") == False
  assert parse(types.Bool, "on") == True

  assert parse(types.TimeDelta, "1s 2h  3w 25m ") == timedelta(seconds=1,
      hours=2, weeks=3, minutes=25)
  assert parse(types.TimeDelta, "4 wEeKs 12.5min") == timedelta(minutes=12.5,
      weeks=4)

  loc = parse(types.File, "/tmp//abc/")
  assert loc.protocol == "file"
  assert str(loc) == "/tmp/abc"

  loc = parse(types.Location, "host:/foo")
  assert loc.host == "host"
  assert loc.path == "/foo"

  enum = types.Enum("First", "Second")
  assert parse(enum, " fIrst") is enum.First
  assert parse(enum, "SECOND") is enum.Second

def test_shouldThrowExceptionIfSyntaxIsWrong(fixture):
  shouldNotParse(types.Positive, "0", "zero", typeDesc="positive number")
  shouldNotParse(types.Positive, "-1", "negative")
  shouldNotParse(types.Positive, "-43")
  shouldNotParse(types.Positive, "blah")

  shouldNotParse(types.Bool, "no truth in here", typeDesc="truth value") 

  shouldNotParse(types.TimeDelta, "4 5 seconds", "unit", "follow")
  shouldNotParse(types.TimeDelta, ".s", "no", "number")
  shouldNotParse(types.TimeDelta, "3 penguins", "unknown", "unit")
  shouldNotParse(types.TimeDelta, "2s 3s", "twice")
  shouldNotParse(types.TimeDelta, "s 5")

  shouldNotParse(types.File, "rsync://host/foo", typeDesc="local file")

  shouldNotParse(types.Location, "rsync:///foo", typeDesc="local path/URL")

  enum = types.Enum("Foo", "Bar", "Quux")
  shouldNotParse(enum, "nope", "Foo", "Quux")

def test_shouldCollectParseErrorsBeforeThrowingException(fixture):
  with pytest.raises(OptionParseException) as ex:
    fixture.parser.parseOptions([optInfo("Opt1", types.Positive),
      optInfo("Opt2", types.Bool)], dict(Opt1="-2", Opt2="foo"))

  iterToTest(ex.value.errors).shouldContainMatchingInAnyOrder(
      lambda error: error.optionName == "Opt1" and "negative" in error.message,
      lambda error: error.optionName == "Opt2" and "truth" in 
        error.expectedType)
