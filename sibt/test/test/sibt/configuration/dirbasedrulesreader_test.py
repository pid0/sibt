from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from test.common.assertutil import iterableContainsInAnyOrder
from sibt.configuration.exceptions import ConfigSyntaxException
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.domain.syncrule import SyncRule
from test.common.rulebuilder import anyRule
import pytest
from datetime import timedelta, time
from test.common import mock
  
class Fixture(object):
  def __init__(self, tmpdir):
    self.rulesDir = tmpdir.mkdir("rules")
    self.enabledDir = tmpdir.mkdir("enabled")
    self.factory = mock.mock()
    
  def writeAnyRule(self, name):
    self.writeRuleFile(name, "[Interpreter]\nName=a\n[Scheduler]\nName=b")
  def writeRuleFile(self, name, contents):
    self.rulesDir.join(name).write(contents)
  def linkToAs(self, ruleName, linkName):
    self.enabledDir.join(linkName).mksymlinkto(self.rulesDir.join(ruleName))
    
  def _createReader(self):
    return DirBasedRulesReader(str(self.rulesDir), str(self.enabledDir), 
        self.factory)
  def read(self):
    return self._createReader().read()
    
def buildCallReturning(matcher, returnValue):
  return mock.callMatchingTuple("build", matcher, ret=returnValue)
def buildCall(matcher):
  return buildCallReturning(matcher, None)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)
  
def test_shouldReadEachFileAsRuleAndConstructRulesWithFactory(fixture):
  fixture.writeAnyRule("rule-1")
  fixture.writeAnyRule("rule-2")

  firstConstructedRule = object()
  secondConstructedRule = object()

  fixture.factory.expectCallsInAnyOrder(
      buildCallReturning(lambda args: args[0] == "rule-1", 
        firstConstructedRule),
      buildCallReturning(lambda args: args[0] == "rule-2",
        secondConstructedRule))

  assert iterableContainsInAnyOrder(fixture.read(), 
      lambda x: x == firstConstructedRule,
      lambda x: x == secondConstructedRule)
  fixture.factory.checkExpectedCalls()

def test_shouldParseInterpreterAndSchedulerOptionsAsValuesInRespectiveSections(
    fixture):
  fixture.writeRuleFile("some-rule", 
      """  [Interpreter]
      
Name=foo
Option1=quux
Option2 = some-value
[Scheduler]
  Name = bar 
  
  Option3 = yes""")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[0] == "some-rule" and
        args[1] == {"Name": "bar", "Option3": "yes"} and
        args[2] == {"Name": "foo", "Option1": "quux", "Option2": "some-value"}))
  fixture.read()
  fixture.factory.checkExpectedCalls()

def test_shouldThrowExceptionIfItEncountersASyntaxError(fixture):
  fixture.writeRuleFile("invalid", "blah")
  with pytest.raises(ConfigSyntaxException):
    fixture.read()

def test_shouldThrowExceptionIfConstructionOfRuleFailsBecauseOfConsistency(
    fixture):
  fixture.writeAnyRule("rule")

  causeEx = ConfigConsistencyException("foo")
  def fail(_):
    raise causeEx

  fixture.factory.expectCallsInAnyOrder(buildCall(fail))
  try:
    fixture.read()
    assert False, "should have thrown"
  except ConfigSyntaxException as ex:
    assert ex.__cause__ == causeEx

  otherEx = Exception("not consistency")
  def totallyFail(_):
    raise otherEx
  fixture.factory.expectCallsInAnyOrder(buildCall(totallyFail))
  try:
    fixture.read()
    assert False
  except Exception as ex:
    assert ex == otherEx


def test_shouldConsiderSymlinkedToRulesEnabled(fixture):
  on = "enabled-rule"
  off = "disabled-rule"
  fixture.writeAnyRule(on)
  fixture.writeAnyRule(off)
  fixture.linkToAs(on, on)
  fixture.linkToAs("/other-file", off)

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[0] == on and args[3] == True),
      buildCall(lambda args: args[0] == off and args[3] == False))
  fixture.read()
  fixture.factory.checkExpectedCalls()


#TODO remove
#def test_shouldParseThreeRuleAttributesFromEachFileInConfigDirectory(fixture):
#  fixture.writeRuleFile("configFile1", """some-tool
#  /from/here
#  
#  /to/there
#  
#  """)
#  fixture.writeRuleFile("configFile2", """
#     other-tool
#  /from/one
#  
#  /to/another-place
#  
#  """)
#  
#  fixture.resultShouldBe(anyConfig().withRules({anyRule().
#    withTitle("configFile1"). 
#    withProgram("some-tool").
#    withSource("/from/here").
#    withDest("/to/there"),
#    anyRule().
#    withTitle("configFile2").
#    withProgram("other-tool").
#    withSource("/from/one").
#    withDest("/to/another-place")}).build())
#  
#def test_shouldIgnoreFilesWhoseNamesArePrefixedWithACapitalN(fixture):
#  fixture.writeRuleFile("n-active", """a-tool
#  /one
#  /two
#  """)
#  fixture.writeRuleFile("Nignore-this", """
#  second-tool
#  /three
#  /four
#  """)
#  
#  fixture.resultShouldBe(anyConfig().withRules({anyRule().
#    withTitle("n-active").
#    withProgram("a-tool").
#    withSource("/one").
#    withDest("/two")}).build())
#  
#def test_shouldParseGlobalConfTimeOfDayRestrictionContentIfExisting(fixture):
#  fixture.writeRuleFile("global.conf", """
#  
#  avoid time of day from 5:00   to  13:15 """)
#  
#  fixture.resultShouldBe(emptyConfig().withTimeOfDayRestriction(
#    TimeRange(time(5, 0), time(13, 15))).build())
#  
#  
#  fixture.writeRuleFile("global.conf", """
#  avoid time of day from 4:12 to 8:2 """)
#  
#  fixture.resultShouldBe(emptyConfig().withTimeOfDayRestriction(
#    TimeRange(time(4, 12), time(8, 2))).build())
#  
#def test_shouldInterpretLastLineAsIntervalOfRule(fixture):
#  fixture.writeRuleFile("every-10-days", """program
#  /src
#  /dest
#  every 10d
#  """)
#  fixture.writeRuleFile("every-4-weeks", """program2
#  /src
#  /dest
#   every   4w
#  """)
#
#  fixture.resultShouldBe(anyConfig().withRules(
#    {anyRule().
#      withTitle("every-10-days").
#      withProgram("program").
#      withSource("/src").
#      withDest("/dest").
#      withInterval(timedelta(days=10)),
#     anyRule().
#      withTitle("every-4-weeks").
#      withProgram("program2").
#      withSource("/src").
#      withDest("/dest").
#      withInterval(timedelta(weeks=4))}).build())
#  
#def test_shouldRaiseExceptionWhenReadingInvalidIntervalTimeUnit(fixture):
#  fixture.writeRuleFile("invalid", """
#  tool
#  /something
#  /2
#  every 2f
#  """)
#  
#  with pytest.raises(ConfigParseException):
#    fixture.read()
#    
#def test_shouldRaiseExceptionWhenRecognizingFormatErrorInIntervalSpecification(
#  fixture):
#  fixture.writeRuleFile("invalid", """
#  tool
#  /1
#  /2
#  every ad
#  """)
#  
#  with pytest.raises(ConfigParseException):
#    fixture.read()
#    
#def test_shouldRaiseExceptionWhenReadingNegativeInterval(fixture):
#  fixture.writeRuleFile("negative-interval", """
#  tool
#  /1
#  /2
#  every -2w
#  """)
#  
#  with pytest.raises(ConfigParseException):
#    fixture.read()
#    
#def test_shouldRaiseExceptionWhenEncounteringInvalidGlobalConfFormat(fixture):
#  fixture.writeRuleFile("global.conf", "avoid time of day from 4:00 to")
#  
#  with pytest.raises(ConfigParseException):
#    fixture.read()
#    
#  fixture.writeRuleFile("global.conf", "avoid time of day from 4:00")
#  
#  with pytest.raises(ConfigParseException):
#    fixture.read()
#    
#def test_shouldRaiseExceptionIfRuleFileHasMoreThanFourNonEmptyLines(fixture):
#  fixture.writeRuleFile("invalid", """
#  some-tool
#  /1
#  /2
#  every 2d
#  
#    more on this line
#  """)
#  
#  with pytest.raises(ConfigParseException):
#    fixture.read()

def containsExactlyOneRuleNamed(rules, name):
  return len([rule for rule in rules if rule.name == name]) == 1
