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
    self.writeRuleFile(name, "[Synchronizer]\nName=a\n[Scheduler]\nName=b")
  def writeRuleFile(self, name, contents):
    self.filePathOf(name).write(contents)
  def writeInstanceFile(self, fileName, contents=""):
    self.enabledDir.join(fileName).write(contents)

  def filePathOf(self, ruleName):
    return self.rulesDir.join(ruleName)
    
  def _createReader(self, prefix):
    return DirBasedRulesReader(str(self.rulesDir), str(self.enabledDir), 
        self.factory, prefix)
  def read(self, namePrefix=""):
    ret = self._createReader(namePrefix).read()
    self.factory.checkExpectedCalls()
    return ret
    
def buildCallReturning(matcher, returnValue):
  return mock.callMatchingTuple("build", matcher, ret=returnValue)
def buildCall(matcher):
  return buildCallReturning(matcher, 5)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)
  
def test_shouldReadEachFileAsARuleAndBuildThemWithFactoryWithPrefixedNames(
    fixture):
  fixture.writeAnyRule("rule-1")
  fixture.writeAnyRule("rule-2")

  firstConstructedRule = object()
  secondConstructedRule = object()

  fixture.factory.expectCallsInAnyOrder(
      buildCallReturning(lambda args: args[0] == "a-rule-1", 
        firstConstructedRule),
      buildCallReturning(lambda args: args[0] == "a-rule-2",
        secondConstructedRule))

  assert iterableContainsInAnyOrder(fixture.read(namePrefix="a-"), 
      lambda x: x == firstConstructedRule,
      lambda x: x == secondConstructedRule)

def test_shouldParseOptionsAsEntriesInRespectiveSectionsIncludingGlobalEntries(
    fixture):
  fixture.writeRuleFile("some-rule", 
      r"""  
      Name = foo
      [Synchronizer]
      
Option1=%(Name)squux
Option2 = some-value%%r
[Scheduler]
  
  Option3 = yes""")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[0] == "some-rule" and
        args[1] == {"Name": "foo", "Option3": "yes"} and
        args[2] == {"Name": "foo", "Option1": "fooquux", 
            "Option2": "some-value%r"}))
  fixture.read()

def test_shouldRemoveOptionsBeginningWithAnUnderscore(fixture):
  fixture.writeRuleFile("rule-with-template-opts",
      """[Synchronizer]
      _Template = bar
      Opt1 = %(_Template)s
        foo
      [Scheduler]
      """)

  fixture.factory.expectCallsInOrder(
      buildCall(lambda args: args[2] == { "Opt1": "bar\nfoo" }))
  fixture.read()

def test_shouldThrowExceptionIfItEncountersASyntaxError(fixture):
  fixture.writeRuleFile("invalid", "blah")
  with pytest.raises(ConfigSyntaxException):
    fixture.read()

  fixture.writeRuleFile("invalid", r"""
  [Scheduler]
  foo = %(_bar)s
  [Synchronizer]
  _bar = 1
  """)
  fixture.writeInstanceFile("@invalid", "")
  with pytest.raises(ConfigSyntaxException):
    fixture.read()

def test_shouldPassOnExceptionIfRuleIsFoundInconsistentByTheFactory(fixture):
  fixture.writeAnyRule("rule")

  consistencyEx = ConfigConsistencyException("rule", "foo", "bar", file=None)
  def fail(_):
    raise consistencyEx

  fixture.factory.expectCalls(buildCall(fail))
  with pytest.raises(ConfigConsistencyException) as ex:
    fixture.read()
  assert ex.value is consistencyEx
  assert ex.value.file == str(fixture.filePathOf("rule"))


  regularEx = Exception("fatal")
  def totallyFail(_):
    raise regularEx
  
  fixture.factory.clearExpectedCalls()
  fixture.factory.expectCalls(buildCall(totallyFail))

  with pytest.raises(Exception) as ex:
    fixture.read()
  assert ex.value == regularEx

def test_shouldIgnoreRuleFilesEndingWithInc(fixture):
  fixture.writeAnyRule("header-rule.inc")

  assert len(fixture.read()) == 0

def test_shouldReadImportedB_nWhenReadingRuleAAndMakeAsSettingsOverrideAnyB_is(
    fixture):
  fixture.writeRuleFile("base.inc", """
  [Synchronizer]
  Loc = /mnt/%(Bar)s
  Base = 3
  Bar = base
  """)
  fixture.writeRuleFile("which-includes-more.inc", "#import base")
  fixture.writeRuleFile("include.inc", """
  [Scheduler]
  Foo = f1
  [Synchronizer]
  Bar = b1""")
  fixture.writeRuleFile("rule", """
  #import which-includes-more
  #import include
  [Synchronizer]
  Interpolated = %(Base)s
  [Scheduler]
  Quux = q2
  Foo = f2""")

  fixture.factory.expectCallsInOrder(mock.callMatchingTuple("build",
      lambda args: args[0] == "rule" and 
      args[1] == {"Foo": "f2", "Quux": "q2"} and
      args[2] == {"Bar": "b1", "Base": "3", "Interpolated": "3", 
        "Loc": "/mnt/b1"}))
  fixture.read()

def test_shouldThrowExceptionIfAnUnknownSectionIsPresent(fixture):
  fixture.writeRuleFile("invalid", """
  [FooSection]
  Lala = 2
  [Scheduler]
  [Synchronizer]
  """)
  with pytest.raises(ConfigSyntaxException) as ex:
    fixture.read()
  assert "FooSection" in str(ex.value)

def test_shouldThrowExceptionIfTheTwoKnownSectionsArentThere(fixture):
  fixture.writeRuleFile("invalid", """
  [Fake1]
  [Fake2]
  Lala = 2
  """)
  with pytest.raises(ConfigSyntaxException):
    fixture.read()

def test_shouldConsiderEnabledRulesAsAsManyAsTheyHaveInstances(fixture):
  fixture.writeAnyRule("on")
  fixture.writeAnyRule("off")
  fixture.writeInstanceFile("@on")
  fixture.writeInstanceFile("foo@on")
  fixture.writeInstanceFile("quux@on")
  fixture.writeInstanceFile("off")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[0] == "on" and args[3] == True),
      buildCall(lambda args: args[0] == "foo@on" and args[3] == True),
      buildCall(lambda args: args[0] == "quux@on" and args[3] == True),
      buildCall(lambda args: args[0] == "off" and args[3] == False))
  fixture.read()

def test_shouldMakeInstanceFileOverrideAllSettingsALastTime(fixture):
  fixture.writeRuleFile("rule", r"""
  _global = base
  [Scheduler]
  [Synchronizer]
  Foo = 1
  Quux = %(_global)s
  Bar = %(Foo)s""")
  fixture.writeInstanceFile("@rule", r"""
  _global = special
  [Synchronizer]
  Foo = 2""")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[2] == { "Foo": "2", "Bar": "2" , 
        "Quux": "special"}))
  fixture.read()

def test_shouldProvideAccessToTheVariablePartOfTheInstanceName(fixture):
  fixture.writeRuleFile("rule", r"""
  [Synchronizer]
  [Scheduler]
  Target = /var/local/vms/%(_instanceName)s.img
  """)
  fixture.writeInstanceFile("ta@ta@rule", "")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(lambda args: args[1] == 
        { "Target": "/var/local/vms/ta@ta.img" }))
  fixture.read()

def test_shouldIgnoreDisabledRulesWithInterpolationErrors(fixture):
  fixture.writeRuleFile("rule", r"""
  [Synchronizer]
  Foo = %(_globalOption)s
  [Scheduler]""")

  fixture.read()
