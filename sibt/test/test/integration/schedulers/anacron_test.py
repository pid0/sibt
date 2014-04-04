import pytest
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from test.common.builders import scheduling, anyScheduling
from test.common import mock
from test.common.pathsbuilder import pathsIn, existingPaths
import os.path
from py._path.local import LocalPath
from test.common.execmock import ExecMock

class Fixture(object):
  def __init__(self, tmpdir):
    self.SibtCall = "/where/sibt/is"
    loader = PyModuleSchedulerLoader("testpackage")
    paths = existingPaths(pathsIn(tmpdir))
    self.mod = loader.loadFromFile("sibt/schedulers/anacron", "anacron", 
        (self.SibtCall, paths))
    self.anaVarDir = LocalPath(paths.varDir).join("anacron")
    self.execs = ExecMock()
    self.mod.impl.processRunner = self.execs

  def run(self, schedulings):
    self.mod.run(schedulings)
    self.execs.check()

  def tabPath(self, tabName):
    return str(self.anaVarDir.join(tabName))
  def tabWithNameShouldContain(self, tabName, expectedLines):
    lines = [line.strip() for line in self.anaVarDir.join(tabName).readlines()]
    for line in expectedLines:
      assert line.format(SibtCall=self.SibtCall) in lines
  def tabShouldBeDeleted(self, tabName):
    assert not os.path.isfile(str(self.anaVarDir.join(tabName)))


@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def anacronCallMatching(matcher):
  return ("/usr/bin/anacron", matcher, "")

#TODO
#next test: check some option (interval)
#next test: use -d option
def test_shouldInvokeAnacronWithGeneratedTabToCallBackToSibt(fixture):
  expectedTabName = "tab-1"

  def checkCall(args):
    assert args[args.index("-t") + 1] == fixture.tabPath(expectedTabName)
    fixture.tabWithNameShouldContain(expectedTabName, [
      "3 0 first-rule {SibtCall} sync-uncontrolled first-rule", 
      "3 0 second-rule {SibtCall} sync-uncontrolled second-rule"
    ])
    return True

  fixture.execs.expectMatchingCalls(anacronCallMatching(checkCall))
  fixture.run([
      scheduling().withRuleName("first-rule"),
      scheduling().withRuleName("second-rule")])

  fixture.tabShouldBeDeleted(expectedTabName)

def test_shouldUseConstantExistingSpoolDirForAnacron(fixture):
  def checkCall(args):
    spoolDir = args[args.index("-S") + 1]
    assert os.path.isdir(spoolDir)
    return True

  fixture.execs.expectMatchingCalls(anacronCallMatching(checkCall))
  fixture.run([anyScheduling()])


def test_shouldCountUpTabNamesIfOtherAnacronInstancesAreRunning(fixture):
  fixture.anaVarDir.join("tab-1").write("")
  fixture.anaVarDir.join("tab-2").write("")
  
  def checkCall(args):
    tab = args[args.index("-t") + 1]
    assert os.path.basename(tab) == "tab-3"
    assert os.path.isfile(tab)
    return True

  fixture.execs.expectMatchingCalls(anacronCallMatching(checkCall))
  fixture.run([anyScheduling()])

#def test_shouldPassIntervalOptionInDaysToAnacron(fixture):
## TODO first call check
#  parser = lambda x:x
#  parser.parseNumberOfDays = lambda string: \
#      1 if string == "a" else 2
