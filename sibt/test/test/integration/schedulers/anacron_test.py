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
  def check(self, scheduling):
    return self.mod.check(scheduling)

  def mockIntervalParser(self):
    ret = lambda x:x
    self.mod.impl.intervalParser = ret
    return ret

  def checkOption(self, optionName, schedulings, matcher):
    self.execs.expectMatchingCalls(anacronCallMatching(
      lambda args: matcher(args[args.index(optionName) + 1])))
    self.run(schedulings)

  def tabShouldContainLinesStartingWith(self, tabPath, *expectedPrefixes):
    lines = [line.strip() for line in LocalPath(tabPath).readlines()]
    for prefix in expectedPrefixes:
      assert any(line.startswith(prefix.format(SibtCall=self.SibtCall)) 
          for line in lines)
  def shouldBeDeleted(self, path):
    assert not os.path.isfile(path)


@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def anacronCallMatching(matcher):
  return ("/usr/bin/anacron", matcher, "")

#TODO
#next test: check some option (interval)
#next test: use -d option
def test_shouldInvokeAnacronWithGeneratedTabToCallBackToSibt(fixture):
  usedTabPath = []
  def checkTab(tabPath):
    usedTabPath.append(tabPath)
    fixture.tabShouldContainLinesStartingWith(tabPath,
        "3 0 first-rule {SibtCall} sync-uncontrolled first-rule", 
        "3 0 second-rule {SibtCall} sync-uncontrolled second-rule"
    )
    return True

  fixture.checkOption("-t", [
      scheduling().withRuleName("first-rule"),
      scheduling().withRuleName("second-rule")], checkTab)

  fixture.shouldBeDeleted(usedTabPath[0])

def test_shouldUseConstantExistingSpoolDirForAnacron(fixture):
  fixture.checkOption("-S", [anyScheduling()], 
      lambda spoolDir: os.path.isdir(spoolDir) and spoolDir.startswith(
          str(fixture.anaVarDir)))

def test_shouldCountUpTabNamesIfOtherAnacronInstancesAreRunning(fixture):
  fixture.anaVarDir.join("tab-1").write("")
  fixture.anaVarDir.join("tab-2").write("")
  
  def checkTab(tab):
    assert os.path.basename(tab) == "tab-3"
    assert os.path.isfile(tab)
    return True

  fixture.checkOption("-t", [anyScheduling()], checkTab)

def test_shouldPassIntervalOptionInDaysToAnacron(fixture):
  assert "Interval" in fixture.mod.availableOptions

  schedulings = [scheduling().
      withRuleName("one-day").
      withOption("Interval", "a").build(),
      scheduling().withRuleName("two-days").
      withOption("Interval", "b").build()]

  parser = fixture.mockIntervalParser()
  parser.parseNumberOfDays = lambda string: \
      1 if string == "a" else 2

  assert fixture.check(schedulings[0]) == []
  assert fixture.check(schedulings[1]) == []
  
  def checkTab(tabPath):
    fixture.tabShouldContainLinesStartingWith(tabPath,
        "1 0 one-day",
        "2 0 two-days")
    return True

  fixture.checkOption("-t", schedulings, checkTab)
def test_shouldCheckIfIntervalSyntaxIsCorrectByCatchingExceptionsOfTheParser(
    fixture):
  errorMessage = "the lazy dog"
  def fail(*args):
    raise Exception(errorMessage)
  failingParser = fixture.mockIntervalParser()
  failingParser.parseNumberOfDays = fail

  assert errorMessage in fixture.check(anyScheduling())[0]

