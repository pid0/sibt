from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
import shutil
from fnmatch import fnmatchcase
from test.common.mockedbasepaths import MockedBasePaths
from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.acceptance.interceptingoutput import InterceptingOutput
from test.common.execmock import ExecMock
from sibt.application.paths import Paths
from py._path.local import LocalPath
import main
import pytest
import os
import os.path
import sys
from datetime import datetime, timezone, timedelta, time
from test.common.constantclock import ConstantClock
from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from test.common import mock
from test.common.mockedschedulerloader import MockedSchedulerLoader
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from test.common.assertutil import iterableContainsInAnyOrder

TestSchedulerPreamble = """
availableOptions = ["Interval", "Syslog"]
def init(*args): pass
"""

class SibtSpecFixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    userDir = tmpdir.join("user")
    sysDir = tmpdir.join("system")

    self.paths = Paths(MockedBasePaths(str(userDir.join("var")),
      str(userDir.join("config"))))
    self.sysPaths = Paths(MockedBasePaths(str(sysDir.join("var")),
      str(sysDir.join("config"))))
    DirTreeNormalizer(self.paths).createNotExistingDirs()

    self.initialTime = datetime.now(timezone.utc)
    self.time = self.initialTime
    self.timeOfDay = time()
    self.testDirNumber = 0
    self.setRootUserId()
    self.schedulerLoader = PyModuleSchedulerLoader("foo")
    self.execs = ExecMock()
  
  def createSysConfigFolders(self):
    DirTreeNormalizer(self.sysPaths).createNotExistingDirs()

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
  def mockTestScheduler(self, name):
    self.writeAnyScheduler(name)
    scheduler = mock.mock()
    scheduler.availableOptions = ["Interval", "Syslog"]
    scheduler.name = name
    self.schedulerLoader = MockedSchedulerLoader({name: scheduler})
    return scheduler

  def testInterpreterOptionsCall(self, path):
    return (path, ("available-options",), "AddFlags\nKeepCopies\n")

  def _writeRule(self, paths, name, contents):
    LocalPath(paths.rulesDir).join(name).write(contents)
  def writeRule(self, name, contents):
    self._writeRule(self.paths, name, contents)
  def _writeAnyRule(self, paths, name, schedulerName, interpreterName):
    self._writeRule(paths, name, ("[Interpreter]\nName = {0}\n" +
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
    exitStatus = main.run(arguments, stdout, stderr, processRunner,
      ConstantClock(self.time, self.timeOfDay), self.paths, self.sysPaths, 
      self.userId, self.schedulerLoader)
    
    self.result = RunResult(stdout, stderr, exitStatus)
    
@pytest.fixture
def fixture(tmpdir):
  return SibtSpecFixture(tmpdir)
    
def test_shouldInvokeTheCorrectConfiguredSchedulersAndInterpreters(fixture):
  fixture.writeRule("foo-rule", """
[Interpreter]
Name = interpreter1
Option=1

[Scheduler]
Name = scheduler1""")

  fixture.writeRule("bar-rule", """[Scheduler]
  Name = scheduler1
[Interpreter]
Name = interpreter2
""")

  fixture.writeScheduler("scheduler1", TestSchedulerPreamble +
"""def run(args): print("scheduled rule '" + args[0].ruleName + "'")
  """)

  fixture.writeInterpreter("interpreter1", """#!/usr/bin/env bash
if [ $1 = "available-options" ]; then
  echo Option
else
  echo one "$2"
fi
  """)

  fixture.writeInterpreter("interpreter2", """#!/usr/bin/env bash
  echo two "$2"
  """)

  fixture.runSibtWithRealStreamsAndExec("sync", "foo-rule")
  fixture.stdoutShouldBe("scheduled rule 'foo-rule'\n")
      
  fixture.runSibtWithRealStreamsAndExec("sync-uncontrolled", "foo-rule")
  fixture.stdoutShouldBe("one Option=1\n")

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
  fixture.writeAnyRule("rule", "is-there", "is-not-there")

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
  [Scheduler]
  Name = sched
  Interval = 2w
  """)

  fixture.execs.expectCalls(fixture.testInterpreterOptionsCall(interPath))
  fixture.runSibtCheckingExecs("sync", calledRuleName)
  sched.checkExpectedCalls()

  fixture.execs.expectCalls(fixture.testInterpreterOptionsCall(interPath),
      (interPath, ("sync", "AddFlags=-X -A"), ""))
  fixture.runSibtCheckingExecs("sync-uncontrolled", calledRuleName)

def test_shouldFailIfOptionsAreUsedThatAreNotExplicitlySupportedByConfiguration(
    fixture):
  fixture.writeTestScheduler("sched")
  fixture.writeTestInterpreter("inter")

  fixture.writeRule("rule", """[Interpreter]
  Name = inter
  AddFlags = foo
  DoesNotExist = abc
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

def test_shouldInitSchedulersCorrectly(fixture):
  fixture.writeScheduler("sched", """availableOptions = []
def init(sibtInvocation, paths, sysPaths): print("{0}{1}{2}".format(
sibtInvocation, paths.configDir, sysPaths.configDir))""")

  fixture.runSibtWithRealStreamsAndExec("list", "schedulers")
  fixture.stdoutShouldContain(sys.argv[0] + fixture.paths.configDir + 
      fixture.sysPaths.configDir + "\n")

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


#def test_shouldBeAbleToReadAndOutputMultipleBackupRulesFromConfFiles(fixture):
#  rule1Src, rule1Dest, rule2Src, rule2Dest = fixture.makeNumberOfTestDirs(4)
#  
#  fixture.writeRuleFile("rule1", """
#  rsync
#  
#    {0}
#  {1}
#  every 7w
#  """.format(rule1Src, rule1Dest))
#  fixture.writeRuleFile("rule2", """
#  rdiff
#  {0}
#  {1}
#  15d
#  """.format(rule2Src, rule2Dest))
#  fixture.writeRuleFile("rule3", """
#  rsync
#  {0}
#  {1}
#  """.format(rule1Src, rule1Dest))
#  
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContainInOrder("rule1", "Using rsync", 
#    'from "{0}"'.format(rule1Src),
#    'to "{0}"'.format(rule1Dest),
#    "run every 7 weeks")
#  
#  fixture.stdoutShouldContainInOrder("rule2", "Using rdiff", 
#    'from "{0}"'.format(rule2Src), 'to "{0}"'.format(rule2Dest),
#    "run every 15 days")
#  
#  fixture.stdoutShouldContainInOrder("rule3", "run every time")
#  fixture.sibtShouldNotExecuteAnyPrograms()
#    
#def test_shouldIgnoreRuleFilesWithNamesPrefixedWithACapitalN(fixture):
#  activeRuleRun = fixture.writeSomeRsyncRule("active-rule")
#  
#  fixture.writeRuleFile("N-inactive-rule", """
#  rdiff-backup
#  /one
#  /two
#  """)
#  
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContain("active-rule", "Using rsync")
#  fixture.stdoutShouldNotContain("inactive-rule", 'from "/one"',
#    "rdiff-backup")
#  fixture.sibtShouldNotExecuteAnyPrograms()
#  
#  fixture.runSibt()
#  fixture.sibtShouldExecute([activeRuleRun])
#  
#def test_shouldRunRsyncWithCorrectOptionsAndSourceEndingWithSlash(fixture):
#  rule1Src = fixture.newTestDir("folder1")
#  rule1Dest = fixture.newTestDir("folder2/")
#  rule2Src = fixture.newTestDir("folder3/")
#  rule2Dest = fixture.newTestDir("folder3/")
#  
#  fixture.writeRuleFile("rsync-rule-1", """
#  rsync
#  {0}
#  {1}
#  """.format(rule1Src, rule1Dest))
#  fixture.writeRuleFile("rsync-rule-2", """
#  rsync
#  {0}
#  {1}
#  """.format(rule2Src, rule2Dest))
#  
#  expectedRule1Src = rule1Src + "/"
#  
#  fixture.runSibt()
#  fixture.stdoutShouldBeEmpty()
#  fixture.sibtShouldExecuteInAnyOrder([
#    ("rsync", ("-a", "--partial", "--delete", expectedRule1Src, rule1Dest)),
#    ("rsync", ("-a", "--partial", "--delete", rule2Src, rule2Dest))])
#  
#def test_shouldRunRdiffBackupWithCorrectOptionOnceForEachRdiffRule(fixture):
#  rule1Src = fixture.newTestDir("folder")
#  rule1Dest = fixture.newTestDir("folder/")
#  rule2Src = fixture.newTestDir("source/")
#  rule2Dest = fixture.newTestDir("dest")
#  
#  fixture.writeRuleFile("rdiff-rule1", """
#  rdiff
#  {0}
#  {1}
#  """.format(rule1Src, rule1Dest))
#  fixture.writeRuleFile("rdiff-rule2", """
#  rdiff
#  {0}
#  {1}""".format(rule2Src, rule2Dest))
#  
#  fixture.runSibt()
#  fixture.sibtShouldExecuteInAnyOrder(
#    [("rdiff-backup", ("--remove-older-than", "2W",
#    rule1Src, rule1Dest)),
#    ("rdiff-backup", ("--remove-older-than", "2W",
#    rule2Src, rule2Dest))])
#  
#def test_ifAFrequencyIsDefinedShouldRunRuleOnlyIfSufficientTimeHasPassed(
#  fixture):
#  firstRuleRun = fixture.writeSomeRsyncRule("unrestrained-rule")
#  secondRuleRun = fixture.writeSomeRsyncRule("every-two-days", "every 2d")
#  thirdRuleRun = fixture.writeSomeRsyncRule("every-three-weeks", "every 3w")
#  
#  def sibtShouldExecuteAtTimeAfterInitialTime(time, programs):
#    fixture.setClockToTimeAfterInitialTime(time)
#    fixture.runSibt()
#    fixture.sibtShouldExecuteInAnyOrder(programs)
#  
#  fixture.runSibt()
#  fixture.sibtShouldExecuteInAnyOrder(
#    [firstRuleRun, secondRuleRun, thirdRuleRun])
#  
#  fixture.runSibt()
#  fixture.sibtShouldExecute([firstRuleRun])
#  
#  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(days=1), [firstRuleRun])
#  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(days=2), 
#    [firstRuleRun, secondRuleRun])
#  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(days=5), 
#    [firstRuleRun, secondRuleRun])
#  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(weeks=3), 
#    [firstRuleRun, secondRuleRun, thirdRuleRun])
#  
#def test_shouldNotRunAnyRulesDuringConfiguredTimeOfDayToAvoid(fixture):
#  ruleRun = fixture.writeSomeRsyncRule("some-rule")
#  
#  def shouldExecuteAt(timeOfDay, shouldExecute):
#    fixture.setTimeOfDay(timeOfDay)
#    fixture.runSibt()
#    if shouldExecute:
#      fixture.sibtShouldExecute([ruleRun])
#    else:
#      fixture.sibtShouldNotExecuteAnyPrograms()
#  
#  fixture.writeGlobalConf("""
#  avoid time of day from 23:00 to 2:00
#  """)
#  
#  shouldExecuteAt(time(22, 58), True)
#  shouldExecuteAt(time(22, 59), True)
#  
#  shouldExecuteAt(time(23, 0), False)
#  shouldExecuteAt(time(23, 5), False)
#  shouldExecuteAt(time(0, 5), False)
#  shouldExecuteAt(time(1, 0), False)
#  shouldExecuteAt(time(2, 0), False)
#  
#  shouldExecuteAt(time(2, 1), True)
#  shouldExecuteAt(time(3, 1), True)
#  shouldExecuteAt(time(16, 0), True)
#  
#  fixture.removeGlobalConf()
#  shouldExecuteAt(time(1, 0), True)
#  
#def test_shouldPrintSyntaxConfErrorsIfTheyExistNDoNothingElseForAnyGivenOptions(
#  fixture):
#  def expectErrorWithConfFile(title, contents, *errors):
#    def checkOutput():
#      fixture.sibtShouldNotExecuteAnyPrograms()
#      fixture.stdoutShouldContain("errors", *errors)
#    fixture.writeRuleFile(title, contents)
#    
#    fixture.runSibt()
#    checkOutput()
#    
#    fixture.runSibt("--list-config")
#    checkOutput()
#    fixture.stdoutShouldNotContain("rsync")
#    
#    fixture.removeConfFile(title)
#    
#  fixture.writeSomeRsyncRule("valid-rule")
#  expectErrorWithConfFile("interval-unit", """
#  rsync
#  /some/place
#  /another/one
#  every 2y
#  """, "invalid interval unit", 'in file "interval-unit"')
#  
#  expectErrorWithConfFile("interval-format", """
#  rsync
#  /some/place
#  /another/one
#  every two days
#  """, "parsing interval", 'in file "interval-format"')
#  
#  expectErrorWithConfFile("global.conf", """
#  avoid time of day from 10:00 to
#  """, "parsing time of day restriction", 'in file "global.conf"')
#  
#  expectErrorWithConfFile("too-many-lines", """
#  rsync
#  /1
#  /2
#  every 5d
#  invalid
#  """, "superfluous lines", 'in file "too-many-lines"')
#  
#def test_shouldOutputGlobalConfInformationWhenListingConfig(fixture):
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContainInOrder("global.conf", 
#    "no time of day restriction")
#  
#  fixture.writeGlobalConf("avoid time of day from 10:00 to  14:02")
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContainInOrder("global.conf", 
#    "won't run", "from 10:00 to 14:02")
#  
#def test_shouldSimplyOutputSemanticErrorsButNeverRunAnyRulesIfTheyArePresent(
#  fixture):
#  def shouldPrintErrorsAndRunNothing(errors, listConfigOutput):
#    fixture.runSibt()
#    fixture.sibtShouldNotExecuteAnyPrograms()
#    fixture.stdoutShouldContainInOrder(*errors)
#    
#    fixture.runSibt("--list-config")
#    fixture.stdoutShouldContainInOrder(*errors + listConfigOutput)
#  
#  srcDir, destDir, srcDir2, destDir2 = fixture.makeNumberOfTestDirs(4)
#  
#  fixture.writeSomeRsyncRule("valid-rule")
#  destinationSubDir = os.path.join(destDir, "some-subdirectory")
#  fixture.writeRuleFile("parent-of-dest-exists", """
#  rsync
#  {0}
#  {1}
#  """.format(srcDir2, destinationSubDir))
#  fixture.runSibt()
#  fixture.sibtShouldAmongOthersExecute(rsyncRun(srcDir2 + "/", 
#    destinationSubDir))
#  
#  fixture.writeRuleFile("unknown-tool", """
#  supersync3000
#  {0}
#  {1}""".format(srcDir, destDir))
#  
#  shouldPrintErrorsAndRunNothing(("errors", "unknown backup program",
#    '"supersync3000"'), ("using supersync3000", 'from "{0}"'.format(srcDir)))
#  
#  fixture.writeRuleFile("source-doesnt-exist", """
#  rsync
#  /some/source
#  {0}""".format(destDir2))
#  
#  shouldPrintErrorsAndRunNothing(("unknown backup program", 
#    "source of", "does not exist", "source-doesnt-exist"), 
#    ('from "/some/source"',))
#  
#  fixture.writeRuleFile("path-exists-but-is-relative", """
#  rsync
#  {0}
#  {1}""".format(srcDir, os.path.relpath(destDir)))
#  shouldPrintErrorsAndRunNothing(("destination of",
#    "relative"), tuple())
#  
#def test_shouldOutputInformationAboutIntervalOfRulesWhenListingConfig(fixture):
#  def dateStringWithDay(day):
#    return "2000-01-{0} 12:00:00.000000 +0000".format(day)
#  
#  fixture.writeSomeRsyncRule("every-week-rule", "every 1w")
#  fixture.writeSomeRsyncRule("unrestricted-rule")
#  fixture.setClockInitialTime(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
#  
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContainInOrder("every-week-rule", 
#    "last time run: n/a",
#    "next time (at the earliest): Due")
#  fixture.stdoutShouldContainInOrder("unrestricted-rule:",
#    "next time (at the earliest): Due")
#  
#  fixture.runSibt()
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContainInOrder("every-week-rule", 
#    "last time run: " + dateStringWithDay("01"),
#    "next time (at the earliest): " + dateStringWithDay("08"))
#  fixture.stdoutShouldContainInOrder("unrestricted-rule:",
#    "next time (at the earliest): Due")
#    
#  fixture.setClockToTimeAfterInitialTime(timedelta(days=4))
#  fixture.runSibt()
#  fixture.runSibt("--list-config")
#  fixture.stdoutShouldContainInOrder("unrestricted-rule:",
#    "last time run: " + dateStringWithDay("05"))
#  fixture.stdoutShouldContainInOrder("every-week-rule",
#    "next time (at the earliest): " + dateStringWithDay("08"))
#  
#  fixture.writeGlobalConf("""
#    avoid time of day from 11:00 to 14:54
#  """)
#  fixture.runSibt("--list-config")
#  
#  fixture.stdoutShouldContainInOrder("unrestricted-rule",
#    "next time (at the earliest): 2000-01-05 14:55:00.000000 +0000")
#  fixture.stdoutShouldContainInOrder("every-week-rule",
#    "next time (at the earliest): 2000-01-08 14:55:00.000000 +0000")
  
  
def rsyncRun(src, dest):
  return ("rsync", ("-a", "--partial", "--delete", src, dest))
