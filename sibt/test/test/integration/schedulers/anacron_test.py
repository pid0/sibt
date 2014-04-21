import pytest
from test.common.servermock import ServerMock
import socket
import time
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from test.common.builders import scheduling, anyScheduling
from test.common import mock
from test.common.pathsbuilder import pathsIn, existingPaths
import os.path
from py.path import local
from test.common.execmock import ExecMock
import sys
from fnmatch import fnmatchcase

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.miscDir = tmpdir.mkdir("misc")

  def init(self, sibtCall=["/where/sibt/is"]):
    loader = PyModuleSchedulerLoader("testpackage")
    paths = existingPaths(pathsIn(self.tmpdir))
    self.mod = loader.loadFromFile("sibt/schedulers/anacron", "anacron", 
        (sibtCall, paths))
    self.anaVarDir = local(paths.varDir) / "anacron"
    self.execs = ExecMock()

  def run(self, schedulings, mockingExecs=True):
    if mockingExecs:
      self.mod.impl.processRunner = self.execs
    self.mod.run(schedulings)
    self.execs.check()
  def check(self, schedulings):
    return self.mod.check(schedulings)

  def runWithMockedSibt(self, sibtProgram, schedulings, sibtArgs=[]):
    sibt = self.miscDir / "sibt"
    self.init([str(sibt)] + sibtArgs)
    sibt.write(sibtProgram)
    sibt.chmod(0o700)
    self.run(schedulings, mockingExecs=False)

  def mockIntervalParser(self):
    ret = lambda x:x
    self.mod.impl.intervalParser = ret
    return ret

  def checkOption(self, optionName, schedulings, matcher):
    self.execs.expectCalls(anacronCallMatching(
      lambda args: matcher(args[args.index(optionName) + 1])))
    self.run(schedulings)

  def tabShouldContainLinesMatching(self, tabPath, *expectedPatterns):
    lines = [line.strip() for line in local(tabPath).readlines()]
    for pattern in expectedPatterns:
      assert any(fnmatchcase(line, pattern) for line in lines)
  def shouldBeDeleted(self, path):
    assert not os.path.isfile(path)


@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def anacronCallMatching(matcher):
  return ("/usr/bin/anacron", matcher, "")

def test_shouldInvokeAnacronWithGeneratedTabToCallBackToSibt(fixture):
  testFile = str(fixture.miscDir / "test")
  assert not os.path.isfile(testFile)

  fixture.runWithMockedSibt("""#!/usr/bin/env bash
  if [[ $1 = --some-global-opt && $2 = 'blah foo' && \
      $3 = sync-uncontrolled && $4 = some-rule ]]; then
    touch {0}
  fi""".format(testFile), [scheduling().withRuleName("some-rule")],
  sibtArgs=["--some-global-opt", "blah foo"])

  assert os.path.isfile(testFile)

def test_shouldUseConstantExistingSpoolDirForAnacron(fixture):
  fixture.init()
  fixture.checkOption("-S", [anyScheduling()], 
      lambda spoolDir: os.path.isdir(spoolDir) and spoolDir.startswith(
          str(fixture.anaVarDir)))

def test_shouldCountUpTabAndScriptNamesNamesIfTheyExistAndDeleteThemAfterwards(
    fixture):
  fixture.init()
  usedTabPath = []
  (fixture.anaVarDir / "script-1").write("")
  (fixture.anaVarDir / "tab-1").write("")
  (fixture.anaVarDir / "tab-2").write("")
  
  def checkTab(tab):
    usedTabPath.append(tab)
    assert os.path.basename(tab) == "tab-3"
    assert os.path.isfile(tab)
    fixture.tabShouldContainLinesMatching(tab, "*script-2*")
    return True

  fixture.checkOption("-t", [anyScheduling()], checkTab)

  fixture.shouldBeDeleted(usedTabPath[0])

def test_shouldPassIntervalOptionInDaysToAnacron(fixture):
  fixture.init()
  assert "Interval" in fixture.mod.availableOptions

  schedulings = [scheduling().
      withRuleName("one-day").
      withOption("Interval", "a").build(),
      scheduling().withRuleName("two-days").
      withOption("Interval", "b").build(),
      scheduling().withRuleName("no-interval").build()]

  parser = fixture.mockIntervalParser()
  parser.parseNumberOfDays = lambda string: \
      1 if string == "a" else 2 if string == "b" else 3

  assert fixture.check(schedulings) == []
  
  def checkTab(tabPath):
    fixture.tabShouldContainLinesMatching(tabPath,
        "3 0 no-interval*",
        "1 0 one-day*",
        "2 0 two-days*")
    return True

  fixture.checkOption("-t", schedulings, checkTab)
def test_shouldCheckIfIntervalSyntaxIsCorrectByCatchingExceptionsOfTheParser(
    fixture):
  fixture.init()
  errorMessage = "the lazy dog"
  def fail(*args):
    raise Exception(errorMessage)
  failingParser = fixture.mockIntervalParser()
  failingParser.parseNumberOfDays = fail

  assert errorMessage in fixture.check([anyScheduling()])[0]

def test_shouldSupportLoggingSibtOutputToFileBeforeAnacronSeesIt(fixture):
  logFile = fixture.miscDir / "log"
  fixture.runWithMockedSibt("""#!/usr/bin/env bash
  if [ $2 = not-logging ]; then
    echo lorem ipsum
  fi
  if [ $2 = logging-2 ]; then
    echo dolor sit
  fi
  if [ $2 = logging ]; then
    echo lazy dog
  fi
  echo quick brown fox >&2
  """, [
      scheduling().withRuleName("not-logging").build(),
      scheduling().withRuleName("logging").
          withOption("LogFile", str(logFile)).build(),
      scheduling().withRuleName("logging-2").withOption("LogFile", 
          str(logFile)).build()])

  log = logFile.read()
  assert "quick brown fox" in log
  assert "lazy dog" in log
  assert "dolor sit" in log
  assert "lorem ipsum" not in log
  
  assert "LogFile" in fixture.mod.availableOptions

def test_shouldSupportSysloggingSibtOutput(fixture):
  fixture.init()
  assert "Syslog" in fixture.mod.availableOptions

  logFile = fixture.tmpdir.join("log")

  message1 = "goes to stdout"
  message2 = "its an error"

  syslogMock = None
  with ServerMock("5024", socket.SOCK_DGRAM) as syslogMock:
    fixture.runWithMockedSibt(
    """#!/usr/bin/env bash
    echo {0}
    echo {1} >&2""".format(message1, message2), 
    [scheduling().
        withOption("LogFile", str(logFile)).
        withOption("Syslog", "yes").
        withOption("SyslogTestOpts", "--server localhost --port 5024").build()])

  syslog = syslogMock.receivedBytes.decode("utf-8")

  assert "sibt: " in syslog
  assert message1 in syslog
  assert message2 in syslog
  assert message1 in logFile.read()
  assert message2 in logFile.read()

  
def test_shouldHaveAnOptionThatTakesAPogramToExecuteWhenSibtFails(fixture):
  testFile = fixture.miscDir / "test"
  testFile2 = str(fixture.miscDir / "test2")
  onFailScript = fixture.miscDir / "on-fail"
  onFailScript.write("""#!/usr/bin/env bash
  if [ $1 = a ]; then
    echo $2 >{0}
  fi""".format(str(testFile)))
  onFailScript.chmod(0o700)

  executingScheduling = scheduling().withOption(
      "ExecOnFailure", "{0} {1} {2}".format(str(onFailScript), "a", "%r")).\
      withOption("LogFile", "/tmp/foo")

  fixture.runWithMockedSibt("""#!/usr/bin/env bash
  if [ $2 = fails ]; then
    exit 1
  else
    touch '{0}'
  fi""".format(testFile2), [
      executingScheduling.withRuleName("fails").build(),
      executingScheduling.withRuleName("doesnt").build()])

  assert os.path.isfile(testFile2)
  assert testFile.read() == "fails\n"

  assert "ExecOnFailure" in fixture.mod.availableOptions

def test_shouldHaveAnInterfaceToAnacronsStartHoursRange(fixture):
  fixture.init()

  assert "AllowedHours" in fixture.mod.availableOptions
  def checkTab(tabPath):
    fixture.tabShouldContainLinesMatching(tabPath, "*START_HOURS_RANGE=6-20")
    return True
  schedulings = [scheduling().withOption("AllowedHours", "6-20").
      build(), anyScheduling()]
  fixture.checkOption("-t", schedulings, checkTab)

  assert fixture.check(schedulings) == []

def test_shouldCheckIfAllowedHoursSettingsAreContradictory(fixture):
  fixture.init()

  assert "contradictory AllowedHours" in \
      fixture.check([
          scheduling().withOption("AllowedHours", "2-5").build(),
          scheduling().withOption("AllowedHours", "3-10").build()])[0]
  assert fixture.check([
      scheduling().withOption("AllowedHours", "12-20").build(),
      scheduling().withOption("AllowedHours", "12-20").build()]) == []

def test_shouldManageToBeInitializedMultipleTimesWithTheSameFolder(fixture):
  fixture.init()
  fixture.init()

