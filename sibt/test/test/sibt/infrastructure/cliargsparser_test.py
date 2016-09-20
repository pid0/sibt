import pytest
from sibt.infrastructure import cliargsparser as cliparser
from sibt.infrastructure.cliargsparser import PosArg, OptArg, SubGroup, \
    SubGroups
from test.common.assertutil import iterToTest

class Fixture(object):
  def __init__(self):
    self.twoOptsParser = cliparser.CliParser([PosArg("in-file"), 
      PosArg("outFile")])
    self.inFilesWithOpts = self.inFilesParser(addOpts=[
      OptArg("foo", noOfArgs="1"),
      OptArg("bar", noOfArgs="0"),
      OptArg("rest", noOfArgs="*")])
    self.parserWithShortOpts = cliparser.CliParser([OptArg("full", "f"),
      OptArg("boolean", "b"),
      OptArg("pattern", "p", noOfArgs="1")])
    self.plusParser = cliparser.CliParser([OptArg("opt"), 
      PosArg("foo", noOfArgs="+")])
    self.parserWithGroups = cliparser.CliParser([
      OptArg("test", noOfArgs="1"), 
      SubGroups(
      SubGroup("foo", OptArg("first", "f"), PosArg("rest", noOfArgs="*")),
      SubGroup(("bar", "two"), OptArg("second", "s"), 
        SubGroups(
        SubGroup("sub1", OptArg("rest", noOfArgs="*"), 
          SubGroups(SubGroup("sub21"), SubGroup("sub22"))),
        SubGroup("sub2", OptArg("abc")))), 
      SubGroup("quux", SubGroups(
        SubGroup("quuxsub1"),
        SubGroup("quuxsub2", PosArg("rest", noOfArgs="*")), 
          default="quuxsub2")), default="foo")
      ])

  def inFilesParser(self, noOfArgs="*", addOpts=[]):
    return cliparser.CliParser([PosArg("output"), 
      PosArg("inFiles", noOfArgs=noOfArgs)] + addOpts)

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldParsePositionalArgsOneAfterTheOther(fixture):
  assert fixture.twoOptsParser.parseArgs(["foo", "-"]).values == \
      {"in-file": "foo", "outFile": "-"}

  assert fixture.inFilesParser().parseArgs(["out", "file1", "foo", "file2"]).\
      values == dict(output="out", inFiles=["file1", "foo", "file2"])
  assert fixture.inFilesParser().parseArgs(["first"]).values == \
      dict(output="first", inFiles=[])

  assert fixture.plusParser.parseArgs(["a", "b"]).values["foo"] == ["a", "b"]

def test_shouldFailIfUnparsedArgumentsRemain(fixture):
  with pytest.raises(cliparser.TooManyArgsException) as ex:
    fixture.twoOptsParser.parseArgs(["foo", "bar", "baz", "quux"])
  assert "too many" in str(ex.value)
  assert ex.value.remainingArgs == ["baz", "quux"]

def test_shouldBeAbleToGiveAUsageStringBasedOnChosenGroupsToThisPoint(fixture):
  assert fixture.inFilesParser().helpString().startswith(
      "<output> [<inFiles...>]")
  assert fixture.plusParser.grammarString() == "[--opt] <foo...>"

  expectedGrammar = "[--test <arg>] <command>"
  assert fixture.parserWithGroups.grammarString(progName="./sibt") == \
      "./sibt " + expectedGrammar
  helpString = fixture.parserWithGroups.helpString()
  assert expectedGrammar in helpString
  assert "foo" in helpString
  assert "bar" in helpString

  with pytest.raises(cliparser.TooFewArgsException) as ex:
    fixture.parserWithGroups.parseArgs(["bar", "sub1"]) 
  assert fixture.parserWithGroups.grammarString(ex.value.groupsTrail) == \
      "[--test <arg>] bar [--second] sub1 [--rest <arg...>] <command3>"

def test_shouldFailIfSomePositionalsCouldNotBeParsed(fixture):
  with pytest.raises(cliparser.TooFewArgsException) as ex:
    fixture.twoOptsParser.parseArgs(["foo"])
  assert ex.value.remainingGrammar == "<outFile>"

  with pytest.raises(cliparser.TooFewArgsException):
    fixture.inFilesParser(noOfArgs="+").parseArgs(["foo"])

  with pytest.raises(cliparser.TooFewArgsException):
    fixture.plusParser.parseArgs(["--opt"])

  with pytest.raises(cliparser.TooFewArgsException) as ex:
    fixture.parserWithGroups.parseArgs(["-s"])
  assert "<command2>" in ex.value.remainingGrammar

def test_shouldParseOptionalsInterleavedInWhateverWay(fixture):
  parserWithBool = cliparser.CliParser([OptArg("do-that")])
  assert parserWithBool.parseArgs(["--do-that"]).values == {"do-that": True}
  assert parserWithBool.parseArgs([]).values == {"do-that": False}

  parserWithVal = cliparser.CliParser([OptArg("some-dir", noOfArgs="1")])
  assert parserWithVal.parseArgs(["--some-dir", "foo"]).values == \
      {"some-dir": "foo"}
  assert parserWithVal.parseArgs([]).values == {}
  assert parserWithVal.parseArgs(["--some-dir=bar"]).values == \
      {"some-dir": "bar"}

  assert fixture.inFilesWithOpts.parseArgs([
      "a", "b", "c", "--bar", "d", "--rest", "a", "b", "--foo=test"]).values ==\
          dict(output="a", inFiles=["b", "c", "d"], bar=True, foo="test", 
          rest=["a", "b"])

  assert fixture.parserWithShortOpts.parseArgs(["-f"]).values == \
      dict(full=True, boolean=False)
  assert fixture.parserWithShortOpts.parseArgs(["-fb", "-pfoo"]).values == \
      dict(full=True, boolean=True, pattern="foo")
  assert fixture.parserWithShortOpts.parseArgs(["-fbpbar"]).values == \
      dict(full=True, boolean=True, pattern="bar")

def test_shouldFailIfOptionalsMissArguments(fixture):
  with pytest.raises(cliparser.MissingOptionalArgsException) as ex:
    fixture.inFilesWithOpts.parseArgs(["--foo"])
  assert ex.value.optName == "--foo"
  assert "<foo>" in ex.value.remainingGrammar

  with pytest.raises(cliparser.MissingOptionalArgsException) as ex:
    fixture.inFilesWithOpts.parseArgs(["--foo", "--bar"])
  assert "<foo>" in ex.value.remainingGrammar

def test_shouldIgnoreOptionalsAfterADoubleDash(fixture):
  assert fixture.inFilesWithOpts.parseArgs(["a", "--foo", "--", "--bar"]).\
      values["foo"] == "--bar"
  assert fixture.inFilesWithOpts.parseArgs(["a", "--rest", "a", "--", "-f"]).\
      values["rest"] == ["a", "-f"]

  assert fixture.twoOptsParser.parseArgs(["--", "a", "b"]).values == \
      { "in-file": "a", "outFile": "b" }

def test_shouldFailIfUnknownOptionalsAreUsed(fixture):
  with pytest.raises(cliparser.UnknownOptionalException) as ex:
    fixture.parserWithShortOpts.parseArgs(["-fa"])
  assert ex.value.printableName == "-a"

  with pytest.raises(cliparser.UnknownOptionalException) as ex:
    fixture.parserWithShortOpts.parseArgs(["--some-dir=blah"])
  assert ex.value.printableName == "--some-dir"

  with pytest.raises(cliparser.UnknownOptionalException) as ex:
    fixture.parserWithGroups.parseArgs(["-z"])

def test_shouldFailIfOptionalsAreUsedTwice(fixture):
  with pytest.raises(cliparser.OptionalUsedTwiceException) as ex:
    fixture.parserWithShortOpts.parseArgs(["--full", "-b", "--full"])
  assert ex.value.optName == "--full"

def test_shouldLetOptionalsInterruptOtherOptionals(fixture):
  result = fixture.inFilesWithOpts.parseArgs(["z", "--rest", "a", "b", "--foo", 
    "c", "d"]).values
  assert result["rest"] == ["a", "b"]
  assert result["inFiles"] == ["d"]

def test_shouldFailIfAFlagIsGivenAValue(fixture):
  with pytest.raises(cliparser.UnexpectedOptionalValueException) as ex:
    fixture.inFilesWithOpts.parseArgs(["z", "--bar=arg"])
  assert ex.value.value == "arg"

def test_shouldProvideANormalizedArgListThatLedToAParsedOption(fixture):
  iterToTest(fixture.inFilesWithOpts.parseArgs(
    ["foo", "--foo=a", "b", "c"]).options.values()).shouldIncludeMatching(
        lambda opt: opt.name == "output" and opt.source == ["foo"],
        lambda opt: opt.name == "inFiles" and opt.source == ["b", "c"],
        lambda opt: opt.name == "bar" and opt.source == [],
        lambda opt: opt.name == "foo" and opt.source == ["--foo", "a"])

  iterToTest(fixture.inFilesWithOpts.parseArgs(
    ["foo", "--bar", "--rest=a", "b"]).options.values()).shouldIncludeMatching(
        lambda opt: opt.name == "bar" and opt.source == ["--bar"],
        lambda opt: opt.name == "rest" and opt.source == ["--rest", "a", "b"])

  iterToTest(fixture.parserWithShortOpts.parseArgs(
    ["-fbpbar"]).options.values()).shouldIncludeMatching(
        lambda opt: opt.source == ["--full"],
        lambda opt: opt.source == ["--boolean"],
        lambda opt: opt.source == ["--pattern", "bar"])

def test_shouldChooseSubGroupsBasedOnASinglePositional(fixture):
  assert fixture.parserWithGroups.parseArgs(["foo"]).values == \
      dict(command="foo", first=False, rest=[])
  assert fixture.parserWithGroups.parseArgs(["ba", "-s", "sub2"]).values == \
      dict(command="bar", command2="sub2", second=True, abc=False)

def test_shouldChooseDefaultGroupIfTheChoiceDoesntMatch(fixture):
  assert fixture.parserWithGroups.parseArgs([]).values == \
      dict(command="foo", first=False, rest=[])

  result = fixture.parserWithGroups.parseArgs(["quux", "nothing"])
  assert result.values == dict(command="quux", command2="quuxsub2", 
      rest=["nothing"])
  assert result.options["command2"].source == ["quuxsub2"]

def test_shouldRequireTheTopLevelChoiceToMatchAGroupIfGiven(fixture):
  with pytest.raises(cliparser.NoSubGroupNameException) as ex:
    fixture.parserWithGroups.parseArgs(["nothing"])
  assert ex.value.givenName == "nothing"

def test_shouldNotNotMatchAGroupIfThePositionalIsJustOneChar(fixture):
  with pytest.raises(cliparser.NoSubGroupNameException):
    fixture.parserWithGroups.parseArgs(["b"])

def test_shouldChooseGroupThatContainsAnUnknownOptional(fixture):
  assert fixture.parserWithGroups.parseArgs(["-s", "sub1", "sub21"]).values == \
      dict(command="bar", second=True, command2="sub1", command3="sub21")

def test_shouldProvideAChosenGroupsTrailOnFailure(fixture):
  with pytest.raises(cliparser.UnknownOptionalException) as ex:
    fixture.parserWithGroups.parseArgs(["two", "sub1", "sub22", "-m"])
  iterToTest(ex.value.groupsTrail).shouldContainMatching(
      lambda group: group.name == "bar",
      lambda group: group.name == "sub1",
      lambda group: group.name == "sub22")

def test_shouldFirstChooseGroupsWithShorterNames(fixture):
  parser = cliparser.CliParser([SubGroups(
    SubGroup("list-files"),
    SubGroup("list"))])

  assert parser.parseArgs(["lis"]).values["command"] == "list"
