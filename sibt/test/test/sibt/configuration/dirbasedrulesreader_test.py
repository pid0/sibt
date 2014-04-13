from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from test.common.assertutil import iterableContainsInAnyOrder
from sibt.configuration.exceptions import ConfigSyntaxException
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.domain.syncrule import SyncRule
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
    ret = self._createReader().read()
    self.factory.checkExpectedCalls()
    return ret
    
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

def test_shouldParseInterpreterAndSchedulerOptionsAsValuesInRespectiveSections(
    fixture):
  fixture.writeRuleFile("some-rule", 
      """  [Interpreter]
      
Name=foo
Option1=%(Name)squux
Option2 = some-value%%r
[Scheduler]
  Name = bar 
  
  Option3 = yes""")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[0] == "some-rule" and
        args[1] == {"Name": "bar", "Option3": "yes"} and
        args[2] == {"Name": "foo", "Option1": "fooquux", 
            "Option2": "some-value%r"}))
  fixture.read()

def test_shouldSwallowOptionsBeginningWithUnderscore(fixture):
  fixture.writeRuleFile("rule-with-template-opts",
      """[Interpreter]
      _Template = bar
      Opt1 = %(_Template)s
        foo
      [Scheduler]
      """)

  fixture.factory.expectCallsInOrder(
      buildCall(lambda args: args[2] == {"Opt1": "bar\nfoo"}))
  fixture.read()

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

def test_shouldIgnoreRuleFilesEndingWithInc(fixture):
  fixture.writeAnyRule("header-rule.inc")

  assert len(fixture.read()) == 0

def test_shouldReadImportsB_nWhenReadingRuleAAndMakeAsSettingsOverrideAnyB_is(
    fixture):
  fixture.writeRuleFile("base.inc", """
  [Interpreter]
  Base = 3
  Bar = base
  """)
  fixture.writeRuleFile("which-includes-more.inc", "#import base")
  fixture.writeRuleFile("include.inc", """
  [Scheduler]
  Foo = f1
  [Interpreter]
  Bar = b1""")
  fixture.writeRuleFile("rule", """
  #import which-includes-more
  #import include
  [Scheduler]
  Quux = q2
  Foo = f2""")

  fixture.factory.expectCallsInOrder(mock.callMatchingTuple("build",
      lambda args: args[0] == "rule" and 
      args[1] == {"Foo": "f2", "Quux": "q2"} and
      args[2] == {"Bar": "b1", "Base": "3"}))
  fixture.read()

def test_shouldThrowExceptionIfAnUnknownSectionIsPresent(fixture):
  fixture.writeRuleFile("invalid", """
  [FooSection]
  Lala = 2
  [Scheduler]
  [Interpreter]
  """)
  with pytest.raises(ConfigSyntaxException):
    fixture.read()

def test_shouldThrowExceptionIfTheTwoKnownSectionsArentThere(fixture):
  fixture.writeRuleFile("invalid", """
  [Fake1]
  [Fake2]
  Lala = 2
  """)
  with pytest.raises(ConfigSyntaxException):
    fixture.read()

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

def containsExactlyOneRuleNamed(rules, name):
  return len([rule for rule in rules if rule.name == name]) == 1
