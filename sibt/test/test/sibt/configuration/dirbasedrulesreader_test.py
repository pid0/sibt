# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from py.path import local
from sibt.configuration import dirbasedrulesreader 
from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
from sibt.configuration.exceptions import MissingConfigValuesException, \
    ConfigConsistencyException
import pytest
from test.common import mock
from test.common.assertutil import iterToTest

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
    return DirBasedRulesReader(fileReader, str(self.rulesDir), 
        str(self.enabledDir), self.factory, prefix)

  def read(self, mockedFileReader=None, namePrefix="", loadLazyRules=True):
    if mockedFileReader is None:
      mockedFileReader = fakeReader()
    ret = self._createReader(namePrefix, fileReader=mockedFileReader).read()
    if loadLazyRules:
      ret = [lazyRule.load() for lazyRule in ret]
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
    
  return mock.callMatchingTuple("readRule", matcher, ret=ret)

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
  
def test_shouldReturnALazyRuleForEachFileAndBuildWithTheFactoryWhenLoadIsCalled(
    fixture):
  fixture.writeAnyRule("rule-1")
  fixture.writeAnyRule("rule-2")

  fileReader = mock.mock()

  lazyRules = fixture.read(fileReader, loadLazyRules=False, namePrefix="a-")
  assert lazyRules[0].name.startswith("a-rule-")

  ruleOpts1, schedOpts1, syncerOpts1, ruleOpts2, schedOpts2, syncerOpts2 = \
      object(), object(), object(), object(), object(), object()

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

  assert iterToTest(rule.load() for rule in lazyRules).\
      shouldContainInAnyOrder(firstConstructedRule, secondConstructedRule)

def test_shouldPassOnExceptionIfRuleIsFoundInconsistentByTheFactory(fixture):
  fixture.writeAnyRule("rule")

  consistencyEx = ConfigConsistencyException("rule", "foo", "bar", file=None)
  def fail(_):
    raise consistencyEx

  fixture.factory.expectCalls(mock.callMatchingTuple("readRule", fail))
  with pytest.raises(ConfigConsistencyException) as ex:
    fixture.read()
  assert ex.value is consistencyEx
  assert ex.value.file == fixture.rulePath("rule")


  regularEx = Exception("fatal")
  def totallyFail(_):
    raise regularEx
  
  fixture.factory.clearExpectedCalls()
  fixture.factory.expectCalls(mock.callMatchingTuple("readRule", totallyFail))

  with pytest.raises(Exception) as ex:
    fixture.read()
  assert ex.value == regularEx

def test_shouldIgnoreRuleFilesEndingWithInc(fixture):
  fixture.writeAnyRule("header-rule.inc")

  assert len(fixture.read()) == 0

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
  fixture.read()

def test_shouldMakeInstanceFileOverrideAllSettingsALastTime(fixture):
  fixture.writeAnyRule("rule")
  fixture.writeInstanceFile("ta@ta@rule")

  reader = mock.mock()
  reader.expectCallsInAnyOrder(readCall(
    paths=[fixture.rulePath("rule"), fixture.instancePath("ta@ta@rule")], 
    instanceArgument="ta@ta",
    ret=sectionsDict()))

  fixture.factory.expectCallsInAnyOrder(buildCall(name="ta@ta@rule"))
  fixture.read(reader)

def test_shouldReturnNameAndBasicInfoOfRulesEvenWithoutBuildingThem(fixture):
  fixture.writeAnyRule("foo")
  fixture.writeAnyRule("bar")
  fixture.writeInstanceFile("@bar")

  iterToTest(fixture.read(mockedFileReader=mock.mock(),
    loadLazyRules=False)).shouldContainMatchingInAnyOrder(
      lambda rule: rule.name == "foo" and not rule.enabled,
      lambda rule: rule.name == "bar" and rule.enabled)

