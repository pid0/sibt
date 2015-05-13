from py.path import local
from sibt.configuration import dirbasedrulesreader 
from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.configuration.exceptions import MissingConfigValuesException, \
    ConfigConsistencyException
import pytest
from test.common import mock
from test.common.assertutil import iterToTest
from sibt.configuration.cachinginifilesetreader import CachingIniFileSetReader

DontCheck = object()
  
class Fixture(object):
  def __init__(self, tmpdir):
    self.rulesDir = tmpdir.mkdir("rules")
    self.enabledDir = tmpdir.mkdir("enabled")
    self.factory = mock.mock()

  def rulePath(self, ruleName):
    return str(self.rulesDir.join(ruleName))
  def instancePath(self, instanceName):
    return str(self.enabledDir.join(instanceName))
    
  def writeAnyRule(self, name):
    self.writeRuleFile(name, "[Synchronizer]\nName=a\n[Scheduler]\nName=b")
  def writeRuleFile(self, name, contents):
    local(self.rulePath(name)).write(contents)
  def writeInstanceFile(self, fileName, contents=""):
    local(self.instancePath(fileName)).write(contents)

  def _createReader(self, prefix, fileReader=None):
    if fileReader is None:
      fileReader = CachingIniFileSetReader(str(self.rulesDir), 
          [dirbasedrulesreader.RuleSec, dirbasedrulesreader.SyncerSec, 
            dirbasedrulesreader.SchedSec])
    return DirBasedRulesReader(fileReader, str(self.rulesDir), 
        str(self.enabledDir), self.factory, prefix)
  def read(self, namePrefix=""):
    ret = self._createReader(namePrefix).read()
    self.factory.checkExpectedCalls()
    return ret

  def readWithMock(self, mockedFileReader=None, namePrefix=""):
    if mockedFileReader is None:
      mockedFileReader = fakeReader()
    ret = self._createReader(namePrefix, fileReader=mockedFileReader).read()
    self.factory.checkExpectedCalls()
    mockedFileReader.checkExpectedCalls()
    return ret
    
def buildCall(name=DontCheck, ruleOpts=DontCheck, schedOpts=DontCheck, 
    syncerOpts=DontCheck, isEnabled=DontCheck, ret=5):
  def matcher(args):
    for arg, expectedArg in zip(args, [name, ruleOpts, schedOpts, syncerOpts, 
      isEnabled]):
      if expectedArg is not DontCheck and arg != expectedArg:
        return False
    return True
    
  return mock.callMatchingTuple("build", matcher, ret=ret)

def readCall(paths, instanceArgument=DontCheck, ret=None):
  def matcher(args):
    if instanceArgument is not DontCheck:
      if args[1] != instanceArgument:
        return False
    return args[0] == paths
  return mock.callMatchingTuple("sectionsFromFiles", matcher, ret=ret)

def sectionsDict(ruleOpts=object(), schedOpts=object(), syncerOpts=object()):
  return { dirbasedrulesreader.RuleSec: ruleOpts,
      dirbasedrulesreader.SchedSec: schedOpts,
      dirbasedrulesreader.SyncerSec: syncerOpts }

def fakeReader():
  ret = mock.mock()
  ret.sectionsFromFiles = lambda *_: sectionsDict()
  return ret

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)
  
def test_shouldReadEachFileAsARuleAndBuildThemWithFactoryWithPrefixedNames(
    fixture):
  fixture.writeAnyRule("rule-1")
  fixture.writeAnyRule("rule-2")

  ruleOpts1, schedOpts1, syncerOpts1, ruleOpts2, schedOpts2, syncerOpts2 = \
      object(), object(), object(), object(), object(), object()

  fileReader = mock.mock()
  fileReader.expectCallsInAnyOrder(
      readCall(paths=[fixture.rulePath("rule-1")], 
        ret=sectionsDict(ruleOpts1, schedOpts1, syncerOpts1)),
      readCall(paths=[fixture.rulePath("rule-2")],
        ret=sectionsDict(ruleOpts2, schedOpts2, syncerOpts2)))

  firstConstructedRule = object()
  secondConstructedRule = object()

  fixture.factory.expectCallsInAnyOrder(
      buildCall(name="a-rule-1", ruleOpts=ruleOpts1, schedOpts=schedOpts1,
        syncerOpts=syncerOpts1, ret=firstConstructedRule),
      buildCall(name="a-rule-2", ruleOpts=ruleOpts2, schedOpts=schedOpts2,
        syncerOpts=syncerOpts2, ret=secondConstructedRule))

  assert iterToTest(fixture.readWithMock(fileReader, namePrefix="a-")).\
      shouldContainInAnyOrder(firstConstructedRule, secondConstructedRule)

def test_shouldPassOnExceptionIfRuleIsFoundInconsistentByTheFactory(fixture):
  fixture.writeAnyRule("rule")

  consistencyEx = ConfigConsistencyException("rule", "foo", "bar", file=None)
  def fail(_):
    raise consistencyEx

  fixture.factory.expectCalls(mock.callMatchingTuple("build", fail))
  with pytest.raises(ConfigConsistencyException) as ex:
    fixture.readWithMock()
  assert ex.value is consistencyEx
  assert ex.value.file == fixture.rulePath("rule")


  regularEx = Exception("fatal")
  def totallyFail(_):
    raise regularEx
  
  fixture.factory.clearExpectedCalls()
  fixture.factory.expectCalls(mock.callMatchingTuple("build", totallyFail))

  with pytest.raises(Exception) as ex:
    fixture.readWithMock()
  assert ex.value == regularEx

def test_shouldIgnoreRuleFilesEndingWithInc(fixture):
  fixture.writeAnyRule("header-rule.inc")

  assert len(fixture.read()) == 0

#TODO: obsolete -> name not there
#def test_shouldThrowExceptionIfTheTwoKnownSectionsArentThere(fixture):
#  fixture.writeRuleFile("invalid", """
#  [Fake1]
#  [Fake2]
#  Lala = 2
#  """)
#  with pytest.raises(ConfigSyntaxException):
#    fixture.read()

def test_shouldConsiderEnabledRulesAsAsManyAsTheyHaveInstances(fixture):
  fixture.writeAnyRule("on")
  fixture.writeAnyRule("off")
  fixture.writeInstanceFile("@on")
  fixture.writeInstanceFile("foo@on")
  fixture.writeInstanceFile("quux@on")
  fixture.writeInstanceFile("off")

  fixture.factory.expectCallsInAnyOrder(
      buildCall(name="on", isEnabled=True),
      buildCall(name="foo@on", isEnabled=True),
      buildCall(name="quux@on", isEnabled=True),
      buildCall(name="off", isEnabled=False))
  fixture.readWithMock()

def test_shouldMakeInstanceFileOverrideAllSettingsALastTime(fixture):
  fixture.writeAnyRule("rule")
  fixture.writeInstanceFile("ta@ta@rule")

  reader = mock.mock()
  reader.expectCallsInAnyOrder(readCall(
    paths=[fixture.rulePath("rule"), fixture.instancePath("ta@ta@rule")], 
    instanceArgument="ta@ta",
    ret=sectionsDict()))

  fixture.factory.expectCallsInAnyOrder(buildCall(name="ta@ta@rule"))
  fixture.readWithMock(reader)

def test_shouldIgnoreDisabledRulesWithInterpolationErrors(fixture):
  fixture.writeRuleFile("rule", "")

  def interpolationError(*_):
    raise MissingConfigValuesException("type", "name")
  reader = mock.mock()
  reader.sectionsFromFiles = interpolationError

  fixture.readWithMock(reader)
