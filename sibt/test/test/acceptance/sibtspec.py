from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
import shutil
from fnmatch import fnmatchcase
from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.acceptance.interceptingoutput import InterceptingOutput
from test.common.execmock import ExecMock
from py._path.local import LocalPath
import main
import pytest
import os
import os.path
import sys
from datetime import datetime, timezone, timedelta, time
from test.common.constantclock import ConstantClock
from test.common import mock
from test.common.mockedschedulerloader import MockedSchedulerLoader
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from test.common.assertutil import iterableContainsInAnyOrder
from test.common.pathsbuilder import existingPaths, pathsIn

TestSchedulerPreamble = """
availableOptions = ["Interval", "Syslog"]
def init(*args): pass
def check(*args): return []
"""

class SibtSpecFixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    userDir = tmpdir.join("user")
    sysDir = tmpdir.join("system")
    readonlyDir = tmpdir.mkdir("usr-share")

    self.paths = existingPaths(pathsIn(userDir, readonlyDir))
    self.sysPaths = pathsIn(sysDir, "")

    self.initialTime = datetime.now(timezone.utc)
    self.time = self.initialTime
    self.timeOfDay = time()
    self.testDirNumber = 0
    self.setRootUserId()
    self.mockedSchedulers = dict()
    self.execs = ExecMock()
  
  def createSysConfigFolders(self):
    self.sysPaths = existingPaths(self.sysPaths)

  def deleteConfigAndVarFolders(self):
    for directory in os.listdir(str(self.tmpdir)):
      shutil.rmtree(str(self.tmpdir) + "/" + directory)

  def enableRule(self, ruleName):
    self.enableRuleAs(ruleName, ruleName)
  def enableRuleAs(self, ruleName, linkName):
    ruleFile = LocalPath(self.paths.rulesDir).join(ruleName)
    LocalPath(self.paths.enabledDir).join(linkName).mksymlinkto(ruleFile)

  def writeScheduler(self, name, contents):
    self._writeScheduler(self.paths, name, contents)
  def _writeScheduler(self, paths, name, contents):
    LocalPath(paths.schedulersDir).join(name).write(contents)
  def _writeAnyScheduler(self, paths, name):
    self._writeScheduler(paths, name, TestSchedulerPreamble)
  def writeAnyScheduler(self, name):
    self._writeAnyScheduler(self.paths, name)
  def writeAnySysScheduler(self, name):
    self._writeAnyScheduler(self.sysPaths, name)
  def mockTestScheduler(self, name, errorMessages=[]):
    self.writeAnyScheduler(name)
    scheduler = mock.mock()
    scheduler.availableOptions = ["Interval", "Syslog"]
    scheduler.name = name
    scheduler.check = lambda *args: errorMessages
    self.mockedSchedulers[name] = scheduler
    return scheduler

  def testInterpreterOptionsCall(self, path):
    return (path, lambda args: args[0] == "available-options", 
        "AddFlags\nKeepCopies\n")

  def _writeRule(self, paths, name, contents):
    LocalPath(paths.rulesDir).join(name).write(contents)
  def writeRule(self, name, contents):
    self._writeRule(self.paths, name, contents)
  def _writeAnyRule(self, paths, name, schedulerName, interpreterName):
    self._writeRule(paths, name, ("[Interpreter]\nName = {0}\nLoc1=\nLoc2=\n" +
        "[Scheduler]\nName={1}").format(interpreterName, schedulerName))
  def writeAnyRuleWithSchedAndInter(self, name):
    schedulerName = name + "-sched"
    interpreterName = name + "-inter"
    self.writeAnyScheduler(schedulerName)
    self.writeAnyInterpreter(interpreterName)
    self.writeAnyRule(name, schedulerName, interpreterName)
  def writeAnyRule(self, name, schedulerName, interpreterName):
    self._writeAnyRule(self.paths, name, schedulerName, interpreterName)
  def writeAnySysRule(self, name, schedulerName, interpreterName):
    self._writeAnyRule(self.sysPaths, name, schedulerName, interpreterName)

  def writeAnyInterpreter(self, name):
    return self._writeAnyInterpreter(self.paths, name)
  def writeAnySysInterpreter(self, name):
    self._writeAnyInterpreter(self.sysPaths, name)
  def _writeAnyInterpreter(self, paths, name):
    return self._writeInterpreter(paths, name, "#!/bin/sh\necho foo")
  def writeShellInterpreter(self, name, contents):
    self._writeInterpreter(self.paths, name, "#!/bin/sh\n" + contents)
  def writeInterpreter(self, name, contents):
    self._writeInterpreter(self.paths, name, contents)
  def _writeInterpreter(self, paths, name, contents):
    path = LocalPath(paths.interpretersDir).join(name)
    path.write(contents)
    path.chmod(0o700)
    return str(path)

  def writeTestScheduler(self, name):
    self.writeScheduler(name, TestSchedulerPreamble)
  def writeTestInterpreter(self, name):
    self.writeShellInterpreter(name, """
      echo KeepCopies
      echo AddFlags""")

  def removeConfFile(self, name):
    self.configDir.join(name).remove()
  def removeGlobalConf(self):
    self.removeConfFile("global.conf")
  def _writeConfigFile(self, name, contents):
    self.configDir.join(name).write(contents)
  def writeGlobalConf(self, contents):
    self._writeConfigFile("global.conf", contents)
  def writeRuleFile(self, name, contents):
    self._writeConfigFile(name, contents)
  def writeSomeRsyncRule(self, title, interval=""): 
    srcDir = self.newTestDir()
    destDir = self.newTestDir()
    self.writeRuleFile(title, """
    rsync
    {0}
    {1}
    {2}
    """.format(srcDir, destDir, interval))
    return rsyncRun(srcDir + "/", destDir)
  
  def makeNumberOfTestDirs(self, number):
    return tuple((self.newTestDir() for _ in range(number)))
  def newTestDir(self, name=None):
    self.testDirNumber = self.testDirNumber + 1
    tmpDir = str(self.tmpdir)
    parentName = os.path.join(tmpDir, "testdir-" + str(self.testDirNumber))
    fullName = parentName if name is None else os.path.join(parentName, name)
    
    os.makedirs(fullName)
    return fullName
    
  def sibtShouldNotExecuteAnyPrograms(self):
    assert self.result.executionLogger.programsList == []
  def sibtShouldAmongOthersExecute(self, expected):
    assert expected in self.result.executionLogger.programsList
  def sibtShouldExecute(self, expected):
    assert self.result.executionLogger.programsList == expected
  def sibtShouldExecuteInAnyOrder(self, expected):
    assert set(self.result.executionLogger.programsList) == set(expected)
  
  def stderrShouldContain(self, *phrases):
    for phrase in phrases:
      assert phrase in self.result.stderr.stringBuffer
  def stdoutShouldBeEmpty(self):
    self.stdoutShouldBe("")
  def stdoutShouldBe(self, expected):
    assert self.result.stdout.stringBuffer == expected
  def _stdoutLines(self):
    return self.result.stdout.stringBuffer.split("\n")[:-1]
  def _stringsShouldContainPatterns(self, strings, patterns):
    for pattern in patterns:
      assert any(fnmatchcase(string, pattern) for string in strings)
  def stdoutShouldContainLinePatterns(self, *patterns):
    lines = self._stdoutLines()
    self._stringsShouldContainPatterns(lines, patterns)
  def stdoutShouldExactlyContainLinePatternsInAnyOrder(self, *patterns):
    lines = self._stdoutLines()
    assert len(lines) == len(patterns)
    self._stringsShouldContainPatterns(lines, patterns)
  def stdoutShouldContainInOrder(self, *expectedPhrases):
    def ascending(numbers):
      return all([x1 < x2 if x1 is not None else True for x1, x2 in 
        zip([None] + numbers, numbers)])
    return ascending([self.result.stdout.stringBuffer.lower().
      index(phrase.lower()) for phrase in expectedPhrases])
  def stdoutShouldContain(self, *expectedPhrases):
    for phrase in expectedPhrases:
      assert phrase.lower() in self.result.stdout.stringBuffer.lower()
  def stdoutShouldNotContain(self, *expectedPhrases):
    for phrase in expectedPhrases:
      assert phrase.lower() not in self.result.stdout.stringBuffer.lower()

  def shouldHaveExitedWithStatus(self, expectedStatus):
    assert self.result.exitStatus == expectedStatus
    
  def setTimeOfDay(self, timeOfDay):
    self.timeOfDay = timeOfDay
  def setClockToTimeAfterInitialTime(self, delta):
    self.time = self.initialTime + delta
  def setClockInitialTime(self, utcTime):
    self.initialTime = self.time = utcTime
    
  def setNormalUserId(self):
    self.userId = 25
  def setRootUserId(self):
    self.userId = 0
  
  def runSibtWithRealStreamsAndExec(self, *arguments):
    def setStdout(newFile):
      sys.stdout = newFile
    def setStderr(newFile):
      sys.stderr = newFile
    with InterceptingOutput(sys.stdout, setStdout, 1) as stdout, \
        InterceptingOutput(sys.stderr, setStderr, 2) as stderr:
      ret = self._runSibt(stdout, stderr, SynchronousProcessRunner(), 
          arguments)
    return ret

  def runSibtCheckingExecs(self, *arguments):
    self.execs.ignoring = False
    self._runSibtMockingExecAndStreams(self.execs, arguments)
  
  def runSibt(self, *arguments):
    self.execs.ignoring = True
    self._runSibtMockingExecAndStreams(self.execs, arguments)

  def _runSibtMockingExecAndStreams(self, execs, arguments):
    stdout = BufferingOutput()
    stderr = BufferingOutput()
    ret = self._runSibt(stdout, stderr, self.execs, arguments)
    self.execs.check()
    self.execs = ExecMock()
    return ret

  def _runSibt(self, stdout, stderr, processRunner, arguments):
    schedulerLoader = PyModuleSchedulerLoader("foo") if \
        len(self.mockedSchedulers) == 0 else \
        MockedSchedulerLoader(self.mockedSchedulers)
    exitStatus = main.run(arguments, stdout, stderr, processRunner,
      ConstantClock(self.time, self.timeOfDay), self.paths, self.sysPaths, 
      self.userId, schedulerLoader)
    
    self.result = RunResult(stdout, stderr, exitStatus)
    
@pytest.fixture
def fixture(tmpdir):
  return SibtSpecFixture(tmpdir)
    
def test_shouldInvokeTheCorrectConfiguredSchedulersAndInterpreters(fixture):
  fixture.writeRule("foo-rule", """
[Interpreter]
Name = interpreter1
Option=1
Loc1=
Loc2=

[Scheduler]
Name = scheduler1""")

  fixture.writeRule("bar-rule", """[Scheduler]
  Name = scheduler1
[Interpreter]
Name = interpreter2
Loc1=
Loc2=
""")

  fixture.writeScheduler("scheduler1", TestSchedulerPreamble +
"""def run(args): print("scheduled rule '" + args[0].ruleName + "'")
  """)

  fixture.writeInterpreter("interpreter1", """#!/usr/bin/env bash
if [ $1 = "available-options" ]; then
  echo Option
else
  echo one 
fi
  """)

  fixture.writeInterpreter("interpreter2", """#!/usr/bin/env bash
  echo two
  """)

  fixture.runSibtWithRealStreamsAndExec("sync", "foo-rule")
  fixture.stdoutShouldBe("scheduled rule 'foo-rule'\n")
      
  fixture.runSibtWithRealStreamsAndExec("sync-uncontrolled", "foo-rule")
  fixture.stdoutShouldBe("one\n")

def test_shouldBeAbleToListOnlyRootUsersConfigurationOptionsToStdout(fixture):
  fixture.createSysConfigFolders()

  fixture.writeAnyRule("rule-1", "sched-1", "inter-1")
  fixture.writeAnyRule("test-rule-2", "sched-2", "inter-1")
  fixture.writeAnyScheduler("sched-1")
  fixture.writeAnyScheduler("sched-2")
  fixture.writeAnyInterpreter("inter-1")
  fixture.writeAnySysInterpreter("where-is-this?")

  fixture.setRootUserId()

  fixture.runSibt("list", "interpreters")
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder("*inter-1*")

  fixture.runSibt("list", "schedulers")
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder("*sched-1*", 
      "*sched-2*")

  fixture.runSibt("list", "rules")
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder("*rule-1*", 
      "*test-rule-2*")

  fixture.runSibt("list")
  fixture.stdoutShouldContainInOrder("interpreters", "inter-1")
  fixture.stdoutShouldContain("rule-1", "test-rule-2", "sched-1", "sched-2")

def test_shouldAutomaticallyCreateFoldersIfTheyDontExist(fixture):
  fixture.deleteConfigAndVarFolders()
  fixture.runSibt()

  for path in [fixture.paths.rulesDir, fixture.paths.schedulersDir,
      fixture.paths.interpretersDir]:
    assert os.path.isdir(path)

def test_ifInvokedAsNormalUserItShouldListSystemConfigAsWellAsTheOwn(fixture):
  fixture.createSysConfigFolders()

  fixture.writeAnyRule("normal-user-rule", "user-sched", "user-inter")
  fixture.writeAnySysRule("system-rule", "system-sched", "system-inter")
  fixture.writeAnyInterpreter("user-inter")
  fixture.writeAnySysInterpreter("system-inter")
  fixture.writeAnyScheduler("user-sched")
  fixture.writeAnySysScheduler("system-sched")

  fixture.setNormalUserId()
  fixture.runSibt()
  fixture.stdoutShouldContainLinePatterns(
      "-*normal-user-rule*",
      "+*system-rule*",
      "*user-inter*",
      "*system-inter*",
      "*user-sched*",
      "*system-sched*")

def test_shouldExitWithErrorMessageIfInvalidSyntaxIsFound(fixture):
  fixture.writeRule("suspect-rule", "sdafsdaf")
  fixture.writeAnyRuleWithSchedAndInter("some-valid-rule")

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("invalid", "suspect-rule")

def test_shouldDistinguishBetweenDisabledAndSymlinkedToEnabledRules(fixture):
  fixture.writeAnyRuleWithSchedAndInter("is-on")
  fixture.writeAnyRuleWithSchedAndInter("is-off")

  fixture.enableRule("is-on")

  fixture.runSibt("list", "rules")
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
      "*is-on*enabled*",
      "*is-off*disabled*")

def test_shouldFailIfConfiguredSchedulerOrInterpreterDoesNotExist(fixture):
  fixture.writeAnyScheduler("is-there")
  fixture.writeAnyRule("invalid-rule", "is-there", "is-not-there")
  fixture.writeAnyRuleWithSchedAndInter("valid-rule")

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("interpreter", "is-not-there", "not found")

def test_shouldPassOptionsAsIsToCorrectSchedulersAndInterpreters(fixture):
  calledRuleName = "some-rule"

  sched = fixture.mockTestScheduler("sched")
  sched.availableOptions = ["Interval"]
  sched.expectCallsInOrder(mock.callMatching("run", lambda schedulings:
      len(schedulings) == 1 and
      schedulings[0].ruleName == calledRuleName and 
      schedulings[0].options == { "Interval": "2w" }))
  
  interPath = fixture.writeAnyInterpreter("inter")

  fixture.writeRule(calledRuleName, """
  [Interpreter]
  Name = inter
  AddFlags = -X -A
  Loc1 = a
  Loc2 = b
  [Scheduler]
  Name = sched
  Interval = 2w
  """)

  fixture.execs.expectMatchingCalls(
      fixture.testInterpreterOptionsCall(interPath))
  fixture.runSibtCheckingExecs("sync", calledRuleName)
  sched.checkExpectedCalls()

  fixture.execs.expectMatchingCalls(
      fixture.testInterpreterOptionsCall(interPath),
      (interPath, lambda args: args[0] == "sync" and 
          set(args[1:]) == {"AddFlags=-X -A", "Loc1=a", "Loc2=b"}, ""))
  fixture.runSibtCheckingExecs("sync-uncontrolled", calledRuleName)

def test_shouldFailIfOptionsAreUsedNotPredefinedOrSupportedByConfiguration(
    fixture):
  fixture.writeTestScheduler("sched")
  fixture.writeTestInterpreter("inter")

  fixture.writeRule("rule", """[Interpreter]
  Name = inter
  AddFlags = foo
  DoesNotExist = abc
  Loc1=
  Loc2=
  [Scheduler]
  Name = sched
  Interval = bar""")

  fixture.runSibtWithRealStreamsAndExec()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("unsupported", "options", "DoesNotExist")

def test_shoulIssureErrorMessageIfRuleNameContainsAComma(fixture):
  fixture.writeAnyRuleWithSchedAndInter("no,comma")

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldContain("invalid character", "no,comma")
def test_shoulIssureErrorMessageIfRuleNameContainsAnAt(fixture):
  fixture.writeAnyRuleWithSchedAndInter("no@at")

  fixture.runSibt()
  fixture.stderrShouldContain("invalid character")
def test_shoulIssureErrorMessageIfRuleNameContainsASpace(fixture):
  fixture.writeAnyRuleWithSchedAndInter("no space")

  fixture.runSibt()
  fixture.stderrShouldContain("invalid character", "no space")

def test_shouldInitSchedulersCorrectly(fixture):
  fixture.writeScheduler("sched", """availableOptions = []
def init(sibtInvocation, paths): print("{0}{1}".format(
sibtInvocation, paths.configDir))""")

  fixture.runSibtWithRealStreamsAndExec("list", "schedulers")
  fixture.stdoutShouldContain(sys.argv[0] + fixture.paths.configDir + "\n")

def test_shouldBeAbleToMatchRuleNameArgsAgainstListOfEnabledRulesAndRunThemAll(
    fixture):
  schedulerName = "scheduler"
  sched = fixture.mockTestScheduler(schedulerName)

  enabledRules = ["rule-a1", "rule-a2", "rule-b"]

  for ruleName in enabledRules + ["disabled-1", "disabled-2"]:
    interpreterName = ruleName + "inter"
    fixture.writeAnyInterpreter(interpreterName)
    fixture.writeAnyRule(ruleName, schedulerName, interpreterName)
  for ruleName in enabledRules:
    fixture.enableRule(ruleName)

  expectedSchedulings = []
  for expectedRuleName in enabledRules[0:2] + ["disabled-2"]:
    expectedSchedulings.append((lambda expected: lambda scheduling:
      scheduling.ruleName == expected)(expectedRuleName))

  sched.expectCallsInAnyOrder(mock.callMatching("run", lambda schedulings:
      iterableContainsInAnyOrder(schedulings, *expectedSchedulings)))

  fixture.runSibt("sync", "*a[0-9]", "disabled-2")
  sched.checkExpectedCalls()

def test_shouldExitWithErrorMessageIfNoRuleNamePatternMatches(fixture):
  sched = fixture.mockTestScheduler("scheduler")
  fixture.writeAnyInterpreter("inter")
  fixture.writeAnyRule("rule", "scheduler", "inter")

  fixture.runSibt("sync", "foo")
  fixture.stderrShouldContain("no such", "rule")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldAddtionallyReadInterpretersAndSchedulersFromReadonlyDir(fixture):
  schedulersDir = LocalPath(fixture.paths.readonlySchedulersDir)
  schedulersDir.mkdir()
  schedulersDir.join("included-scheduler").write(TestSchedulerPreamble)

  interpretersDir = LocalPath(fixture.paths.readonlyInterpretersDir)
  interpretersDir.mkdir()
  interpreterPath = interpretersDir.join("included-interpreter")
  interpreterPath.write("")
  interpreterPath.chmod(0o700)

  fixture.runSibt()
  fixture.stdoutShouldContainLinePatterns(
      "*included-interpreter*", "*included-scheduler*")

def test_shouldBeAbleToOverrideDefaultPathsWithCommandLineOptions(fixture):
  newConfigDir = fixture.tmpdir.mkdir("foo")
  newSchedulersDir = newConfigDir.mkdir("schedulers")
  newSchedulersDir.join("jct-scheduler").write(TestSchedulerPreamble)

  fixture.runSibt("--config-dir=" + str(newConfigDir), "list", "schedulers")
  fixture.stdoutShouldContain("jct-scheduler")

def test_shouldConsiderNameLoc1AndLoc2AsMinimumAndAlreadyAvailableOptions(
    fixture):
  fixture.writeTestScheduler("test-scheduler")
  fixture.writeAnyInterpreter("inter")

  fixture.writeRule("invalid-rule", 
      "[Interpreter]\nName=inter\n[Scheduler]\nName=test-scheduler")

  fixture.runSibt()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("invalid-rule", "minimum", "Loc1")

def test_shouldProvideAWayToImportRuleConfigsAndANamingSchemeForIncludeFiles(
    fixture):
  scheduler = fixture.mockTestScheduler("sched")
  fixture.writeTestInterpreter("inter")

  fixture.enableRule("header.inc")
  fixture.enableRule("rule")

  fixture.writeRule("header.inc", """
[Scheduler]
Name = sched
Interval = 3w
[Interpreter]
Name = inter
""")

  fixture.writeRule("rule", """
#import header
[Interpreter]
Loc1=
Loc2=
[Scheduler]
Syslog = yes""")

  scheduler.expectCallsInOrder(mock.callMatching("run", lambda schedulings:
      schedulings[0].ruleName == "rule" and schedulings[0].options == {
          "Interval": "3w", "Syslog": "yes"}))

  fixture.runSibt("sync", "*")
  scheduler.checkExpectedCalls()

def test_shouldCheckOptionsBeforeSchedulingRulesAndAbortIfAnErrorOccurs(
    fixture):
  sched = fixture.mockTestScheduler("uncontent-scheduler", 
      errorMessages=["this problem cannot be solved"])
  sched2 = fixture.mockTestScheduler("content-scheduler")
  fixture.writeAnyInterpreter("foo-inter")

  fixture.writeAnyRule("badly-configured-rule", "uncontent-scheduler", 
      "foo-inter")
  fixture.writeAnyRule("correctly-configured-rule", "content-scheduler", 
      "foo-inter")

  fixture.enableRule("badly-configured-rule")
  fixture.enableRule("correctly-configured-rule")

  fixture.runSibt("sync", "*")
  fixture.stderrShouldContain("in badly-configured-rule", 
    "this problem cannot be solved")


