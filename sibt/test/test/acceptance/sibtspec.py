from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
import shutil
from sibt.infrastructure.fileobjoutput import FileObjOutput
from fnmatch import fnmatchcase
from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.common.execmock import ExecMock
from py.path import local
from sibt import main
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
def run(*args): pass
"""
RuleFormat = """
    [Interpreter]
    Name = {{0}}
    Loc1={loc1}
    Loc2={loc2}
    [Scheduler]
    Name={{1}}"""

class SibtSpecFixture(object):
  def __init__(self, tmpdir, capfd):
    self.tmpdir = tmpdir
    userDir = tmpdir / "user"
    sysDir = tmpdir / "system"
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
    self.capfd = capfd

  def validLocForInterpreter(self, name=None, create=True):
    if name is None:
      self.testDirNumber += 1
      ret = self.tmpdir.join("loc-" + str(self.testDirNumber))
    else:
      ret= self.tmpdir.join(name)

    if create:
      os.makedirs(str(ret))

    ret.join("file").write("")
    return str(ret)

  def formatValidLocs(self, ruleString):
    return ruleString.format(loc1=self.validLocForInterpreter(), 
        loc2=self.validLocForInterpreter())

  
  def createSysConfigFolders(self):
    self.sysPaths = existingPaths(self.sysPaths)

  def deleteConfigAndVarFolders(self):
    for directory in os.listdir(str(self.tmpdir)):
      shutil.rmtree(str(self.tmpdir) + "/" + directory)

  def enableRule(self, ruleName):
    self.enableRuleAs(ruleName, ruleName)
  def enableRuleAs(self, ruleName, linkName):
    ruleFile = local(self.paths.rulesDir).join(ruleName)
    local(self.paths.enabledDir).join(linkName).mksymlinkto(ruleFile)

  def writeScheduler(self, name, contents):
    self._writeScheduler(self.paths, name, contents)
  def _writeScheduler(self, paths, name, contents):
    local(paths.schedulersDir).join(name).write(contents)
  def _writeAnyScheduler(self, paths, name):
    self._writeScheduler(paths, name, TestSchedulerPreamble)
  def writeAnyScheduler(self, name):
    self._writeAnyScheduler(self.paths, name)
  def writeAnySysScheduler(self, name):
    self._writeAnyScheduler(self.sysPaths, name)
  def mockTestScheduler(self, name, isSysConfig=False):
    if isSysConfig:
      self.writeAnySysScheduler(name)
    else:
      self.writeAnyScheduler(name)

    scheduler = mock.mock()
    scheduler.availableOptions = ["Interval", "Syslog"]
    scheduler.name = name
    scheduler.check = lambda *args: []
    self.mockedSchedulers[name] = scheduler
    return scheduler

  def testInterpreterOptionsCall(self, path):
    return (path, lambda args: args[0] == "available-options", 
        "AddFlags\nKeepCopies\n")
  def writesToInterCallsAllowed(self, path):
    return (path, lambda args: args[0] == "writes-to", "", {"anyNumber": True})
  def optionsInterCallsAllowed(self, path):
    return (path, lambda args: args[0] == "available-options", "", 
        {"anyNumber": True})

  def _writeRule(self, paths, name, contents):
    local(paths.rulesDir).join(name).write(contents)
  def writeSysRule(self, name, contents):
    self._writeRule(self.sysPaths, name, contents)
  def writeRule(self, name, contents):
    self._writeRule(self.paths, name, contents)
  def _writeAnyRule(self, paths, name, schedulerName, interpreterName):
    self._writeRule(paths, name, self.formatValidLocs(RuleFormat).format(
        interpreterName, schedulerName))
  def writeRuleWithSchedAndInter(self, name=None, loc1=None, loc2=None,
      interpreterName=None, schedulerName=None, sysRule=False):
    if name is None:
      self.testDirNumber += 1
      name = "rule-" + str(self.testDirNumber)

    if schedulerName is None:
      schedulerName = name + "-sched"
      self.writeAnyScheduler(schedulerName)

    if interpreterName is None:
      interpreterName = name + "-inter"
      self.writeAnyInterpreter(interpreterName)

    loc1 = self.validLocForInterpreter() if loc1 is None else loc1
    loc2 = self.validLocForInterpreter() if loc2 is None else loc2

    paths = self.sysPaths if sysRule else self.paths

    self._writeRule(paths, name, RuleFormat.format(loc1=loc1, loc2=loc2).\
        format(interpreterName, schedulerName))

  def writeAnyRule(self, name, schedulerName, interpreterName):
    self._writeAnyRule(self.paths, name, schedulerName, interpreterName)
  def writeAnySysRule(self, name, schedulerName, interpreterName):
    self._writeAnyRule(self.sysPaths, name, schedulerName, interpreterName)

  def writeRunner(self, name):
    os.makedirs(self.paths.runnersDir)
    runnerPath = local(self.paths.runnersDir).join(name)
    runnerPath.write("#!/usr/bin/env bash\necho $1")
    runnerPath.chmod(0o700)
    return str(runnerPath)

  def writeAnyInterpreter(self, name):
    return self._writeAnyInterpreter(self.paths, name)
  def writeAnySysInterpreter(self, name):
    self._writeAnyInterpreter(self.sysPaths, name)
  def _writeAnyInterpreter(self, paths, name):
    return self._writeInterpreter(paths, name, "#!/bin/sh\necho foo")
  def writeShellInterpreter(self, name, contents):
    self._writeInterpreter(self.paths, name, "#!/bin/sh\n" + contents)
  def writeInterpreter(self, name, contents):
    return self._writeInterpreter(self.paths, name, contents)
  def _writeInterpreter(self, paths, name, contents):
    path = local(paths.interpretersDir).join(name)
    path.write(contents)
    path.chmod(0o700)
    return str(path)

  def writeTestScheduler(self, name):
    self.writeScheduler(name, TestSchedulerPreamble)
  def writeTestInterpreter(self, name):
    self.writeShellInterpreter(name, """
      echo KeepCopies
      echo AddFlags""")

  def stderrShouldBeEmpty(self):
    assert self.result.stderr == ""
  def stderrShouldContain(self, *phrases):
    for phrase in phrases:
      assert phrase in self.result.stderr
  def stdoutShouldBeEmpty(self):
    self.stdoutShouldBe("")
  def stdoutShouldBe(self, expected):
    assert self.result.stdout == expected
  def _stdoutLines(self):
    return self.result.stdout.split("\n")[:-1]
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
    return ascending([self.result.stdout.lower().
      index(phrase.lower()) for phrase in expectedPhrases])
  def stdoutShouldContain(self, *expectedPhrases):
    for phrase in expectedPhrases:
      assert phrase.lower() in self.result.stdout.lower()
  def stdoutShouldNotContain(self, *notExpectedPhrases):
    for phrase in notExpectedPhrases:
      assert phrase.lower() not in self.result.stdout.lower()

  def shouldHaveExitedWithStatus(self, expectedStatus):
    assert self.result.exitStatus == expectedStatus
    
  def setNormalUserId(self):
    self.userId = 25
  def setRootUserId(self):
    self.userId = 0
  
  def runSibtWithRealStreamsAndExec(self, *arguments):
    exitStatus = self._runSibt(FileObjOutput(sys.stdout), 
        FileObjOutput(sys.stderr), SynchronousProcessRunner(), arguments)
    stdout, stderr = self.capfd.readouterr()
    self.result = RunResult(stdout, stderr, exitStatus)

  def runSibtCheckingExecs(self, *arguments):
    self.execs.ignoring = False
    self._runSibtMockingExecAndStreams(self.execs, arguments)
  
  def runSibt(self, *arguments):
    self.execs.ignoring = True
    self._runSibtMockingExecAndStreams(self.execs, arguments)

  def _runSibtMockingExecAndStreams(self, execs, arguments):
    stdout = BufferingOutput()
    stderr = BufferingOutput()
    exitStatus = self._runSibt(stdout, stderr, self.execs, arguments)
    self.execs.check()
    self.execs = ExecMock()
    self.result = RunResult(stdout.stringBuffer, stderr.stringBuffer,
        exitStatus)

  def _runSibt(self, stdout, stderr, processRunner, arguments):
    schedulerLoader = PyModuleSchedulerLoader("foo") if \
        len(self.mockedSchedulers) == 0 else \
        MockedSchedulerLoader(self.mockedSchedulers)
    exitStatus = main.run(arguments, stdout, stderr, processRunner,
      self.paths, self.sysPaths, self.userId, schedulerLoader)
    
    return exitStatus
    
@pytest.fixture
def fixture(tmpdir, capfd):
  return SibtSpecFixture(tmpdir, capfd)
    
def test_shouldInvokeTheCorrectConfiguredSchedulersAndInterpreters(fixture):
  fixture.writeRule("foo-rule", fixture.formatValidLocs("""
[Interpreter]
Name = interpreter1
Option=1
Loc1={loc1}
Loc2={loc2}

[Scheduler]
Name = scheduler1"""))

  fixture.writeRule("bar-rule", fixture.formatValidLocs("""[Scheduler]
  Name = scheduler1
[Interpreter]
Name = interpreter2
Loc1={loc1}
Loc2={loc2}
"""))

  fixture.writeScheduler("scheduler1", TestSchedulerPreamble +
"""def run(args): print("scheduled rule '" + args[0].ruleName + "'")
  """)

  fixture.writeInterpreter("interpreter1", """#!/usr/bin/env bash
if [ $1 = available-options ]; then
  echo Option
elif [ $1 = sync ]; then  
  echo one 
fi
  """)

  fixture.writeInterpreter("interpreter2", """#!/usr/bin/env bash
  if [ $1 = sync ]; then  
    echo two
  fi
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
  fixture.writeRuleWithSchedAndInter("some-valid-rule")

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("invalid", "suspect-rule")

def test_shouldDistinguishBetweenDisabledAndSymlinkedToEnabledRules(fixture):
  fixture.writeRuleWithSchedAndInter("is-on")
  fixture.writeRuleWithSchedAndInter("is-off")

  fixture.enableRule("is-on")

  fixture.runSibt("list", "rules")
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
      "*is-on*enabled*",
      "*is-off*disabled*")

def test_shouldFailIfConfiguredSchedulerOrInterpreterDoesNotExist(fixture):
  fixture.writeAnyScheduler("is-there")
  fixture.writeAnyRule("invalid-rule", "is-there", "is-not-there")
  fixture.writeRuleWithSchedAndInter("valid-rule")

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("interpreter", "is-not-there", "not found")

def test_shouldPassOptionsAsIsToCorrectSchedulersAndInterpreters(fixture):
  calledRuleName = "some-rule"
  
  interPath = fixture.writeAnyInterpreter("inter")

  loc1 = fixture.validLocForInterpreter()
  loc2 = fixture.validLocForInterpreter()
  fixture.writeRule(calledRuleName, """
  [Interpreter]
  Name = inter
  AddFlags = -X -A
  Loc1 = {0}
  Loc2 = {1}
  [Scheduler]
  Name = sched
  Interval = 2w
  """.format(loc1, loc2))

  def expectSetupInterpreterCalls():
    fixture.execs.expectCalls(
        fixture.writesToInterCallsAllowed(interPath),
        fixture.testInterpreterOptionsCall(interPath))

  sched = fixture.mockTestScheduler("sched")
  sched.availableOptions = ["Interval"]
  sched.expectCallsInAnyOrder(mock.callMatching("run", lambda schedulings:
      len(schedulings) == 1 and
      schedulings[0].ruleName == calledRuleName and 
      schedulings[0].options == { "Interval": "2w" }))

  expectSetupInterpreterCalls()
  fixture.runSibtCheckingExecs("sync", calledRuleName)
  sched.checkExpectedCalls()

  expectSetupInterpreterCalls()
  fixture.execs.expectCalls((interPath, lambda args: args[0] == "sync" and 
          set(args[1:]) == {"AddFlags=-X -A", "Loc1=" + loc1, "Loc2=" + loc2}, 
          ""))
  fixture.runSibtCheckingExecs("sync-uncontrolled", calledRuleName)

def test_shouldFailIfOptionsAreUsedNotPredefinedOrSupportedByConfiguration(
    fixture):
  fixture.writeTestScheduler("sched")
  fixture.writeTestInterpreter("inter")

  fixture.writeRule("rule", fixture.formatValidLocs("""[Interpreter]
  Name = inter
  AddFlags = foo
  DoesNotExist = abc
  Loc1={loc1}
  Loc2={loc2}
  [Scheduler]
  Name = sched
  Interval = bar"""))

  fixture.runSibtWithRealStreamsAndExec()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("unsupported", "options", "DoesNotExist")

def test_shoulIssureErrorMessageIfRuleNameContainsAComma(fixture):
  fixture.writeRuleWithSchedAndInter("no,comma")

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldContain("invalid character", "no,comma")
def test_shoulIssureErrorMessageIfRuleNameContainsAnAt(fixture):
  fixture.writeRuleWithSchedAndInter("no@at")

  fixture.runSibt()
  fixture.stderrShouldContain("invalid character")
def test_shoulIssureErrorMessageIfRuleNameContainsASpace(fixture):
  fixture.writeRuleWithSchedAndInter("no space")

  fixture.runSibt()
  fixture.stderrShouldContain("invalid character", "no space")

def test_shouldInitSchedulersCorrectlyIncludingSibtInvocationWithGlobalOpts(
    fixture):
  fixture.writeScheduler("sched", """availableOptions = []
def init(sibtInvocation, paths): print("{0},{1}".format(
" ".join(sibtInvocation), paths.configDir))""")

  newReadonlyDir = str(fixture.tmpdir)

  fixture.runSibtWithRealStreamsAndExec("--readonly-dir", newReadonlyDir, 
      "list", "schedulers")
  fixture.stdoutShouldContain("{0} --readonly-dir {1}".format(sys.argv[0],
      newReadonlyDir) + "," +
      fixture.paths.configDir + "\n")

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
  fixture.stderrShouldContain("no matching rule", "foo")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldIgnoreSysRulesWhenSyncing(fixture):
  fixture.createSysConfigFolders()

  sched = fixture.mockTestScheduler("sys-sched", isSysConfig=True)
  fixture.writeAnySysInterpreter("sys-inter")
  fixture.writeAnySysRule("sys-rule", "sys-sched", "sys-inter")

  fixture.setNormalUserId()

  fixture.runSibt("sync", "sys-rule")
  fixture.stderrShouldContain("no matching", "sys-rule")

def test_shouldSupportCommandLineOptionToCompletelyIgnoreSysConfig(fixture):
  fixture.createSysConfigFolders()

  fixture.writeAnyScheduler("own-sched")
  fixture.writeAnySysScheduler("systemd")
  fixture.writeAnySysInterpreter("tar")
  fixture.writeAnySysRule("os-backup", "systemd", "tar")

  fixture.setNormalUserId()

  fixture.runSibt("--no-sys-config", "list")
  fixture.stdoutShouldContain("own-sched")
  fixture.stdoutShouldNotContain("systemd", "tar", "os-backup")

def test_shouldAdditionallyReadInterpretersAndSchedulersFromReadonlyDir(
    fixture):
  schedulersDir = local(fixture.paths.readonlySchedulersDir)
  schedulersDir.mkdir()
  schedulersDir.join("included-scheduler").write(TestSchedulerPreamble)

  interpretersDir = local(fixture.paths.readonlyInterpretersDir)
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
  fixture.writeAnyScheduler("sched")
  fixture.writeTestInterpreter("inter")

  fixture.writeRule("header.inc", """
[Scheduler]
Name = sched
Interval = 3w
[Interpreter]
Name = inter
""")

  ruleName = "actual-rule"
  fixture.writeRule(ruleName, fixture.formatValidLocs("""
#import header
[Interpreter]
Loc1={loc1}
Loc2={loc2}
[Scheduler]
Syslog = yes"""))

  fixture.runSibt("show", ruleName)
  fixture.stdoutShouldContainLinePatterns(
      "*actual-rule*",
      "*Interval = 3w*",
      "*Syslog = yes*",
      "*Loc1 =*")

  fixture.runSibt("show", "header.inc")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("no", "rule")
  fixture.stdoutShouldBeEmpty()

def test_shouldMakeSchedulersCheckOptionsBeforeSchedulingAndAbortIfErrorsOccur(
    fixture):
  sched = fixture.mockTestScheduler("uncontent-scheduler")
  sched.check = lambda schedulings: ["this problem cannot be solved"] if \
      len(schedulings) == 2 else []
  sched2 = fixture.mockTestScheduler("content-scheduler")
  fixture.writeAnyInterpreter("foo-inter")

  fixture.writeAnyRule("badly-configured-rule", "uncontent-scheduler", 
      "foo-inter")
  fixture.writeAnyRule("second-bad", "uncontent-scheduler", 
      "foo-inter")
  fixture.writeAnyRule("correctly-configured-rule", "content-scheduler", 
      "foo-inter")

  fixture.enableRule("badly-configured-rule")
  fixture.enableRule("second-bad")
  fixture.enableRule("correctly-configured-rule")

  fixture.runSibt("sync", "*")
  fixture.stderrShouldContain(" in ", "badly-configured-rule", "second-bad",
      "this problem cannot be solved")

def test_shouldFailAndPrintErrorIfInterpreterReturnsNonZero(fixture):
  fixture.writeAnyScheduler("sched")
  fixture.writeInterpreter("failing-inter", """#!/usr/bin/env bash
exit 1""")
  fixture.writeAnyRule("rule", "sched", "failing-inter")

  fixture.runSibtWithRealStreamsAndExec()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldContain("failing-inter", "error", "calling")

def test_shouldCollectVersionsOfAFileFromRulesThatHaveItWithinLoc1OrLoc2(
    fixture):
  fixture.createSysConfigFolders()
  fixture.setNormalUserId()

  utcThirdOfMarch = "2014-01-03T18:35:00"
  utc123 = "1970-01-01T00:02:03"
  utc0 = "1970-01-01T00:00:00"

  testDir = fixture.tmpdir.mkdir("versions-test")

  fixture.writeInterpreter("has-different-versions-for-locs", 
"""#!/usr/bin/env bash
if [[ $1 = versions-of && $2 = folder/some-file && $4 =~ ^Loc.* ]]; then
  relativeToLoc=$3
  if [ $relativeToLoc = 1 ]; then
    echo '2014-01-03T20:35:00+02:00'
    echo '0'
  fi
  if [ $relativeToLoc = 2 ]; then
    echo 123
  fi
fi""")

  fixture.writeRuleWithSchedAndInter(
      name="rule-1",
      interpreterName="has-different-versions-for-locs",
      loc1="{0}/home/foo/data".format(testDir),
      loc2="{0}/mnt/backup/data".format(testDir),
      sysRule=True)

  fixture.writeRuleWithSchedAndInter(
      name="rule-2",
      interpreterName="has-different-versions-for-locs",
      loc1="{0}/mnt/backup/data".format(testDir),
      loc2="{0}/mnt/remote".format(testDir))

  symlink = fixture.tmpdir.join("link")
  symlink.mksymlinkto(
      "{0}/home/foo/data/folder/some-file".format(testDir))

  with fixture.tmpdir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of", 
        "link")
    fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
        "*rule-1," + utcThirdOfMarch + "*",
        "*rule-1," + utc0 + "*")

  with testDir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of",
        "mnt/backup/data/folder/some-file")
    fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
        "*rule-1," + utc123 + "*",
        "*rule-2," + utcThirdOfMarch + "*",
        "*rule-2," + utc0 + "*")

def test_shouldCorrectlyCallRestoreForTheVersionThatHasAllGivenSubstrings(
    fixture):
  interPath = fixture.writeAnyInterpreter("inter")
  fixture.writeAnyScheduler("sched")

  ruleConfig = """
  [Scheduler]
  Name = sched
  [Interpreter]
  Name = inter
  Loc1 = /mnt/data
  """
  fixture.writeRule("total-backup", ruleConfig + 
      "Loc2 = /mnt/backup")
  fixture.writeRule("other-rule", ruleConfig + 
      "Loc2 = /mnt/quux")

  april5th = "2014-04-05T13:35:34+00:00"
  march3th = "2014-03-30T21:43:12+00:00"
  april5thTimestamp = "1396704934"

  fileName = "file-to-restore"

  setupCalls = (fixture.optionsInterCallsAllowed(interPath),
      fixture.writesToInterCallsAllowed(interPath),
      (interPath, lambda args: args[0] == "versions-of", 
          "\n".join([april5th, march3th]), {"anyNumber": True}))

  def callRestore(*patternsAndDest):
    fixture.runSibtCheckingExecs("--utc", "restore", "/mnt/data/" + fileName,
        *patternsAndDest)

  def expectInterRestoreCall():
    fixture.execs.expectCalls(
        (interPath, lambda args: 
            args[0] == "restore" and 
            "Loc2=/mnt/backup" in args and 
            args[1:6] == (fileName, "1", april5th, april5thTimestamp, 
                "dest.backup"),
            ""))

        
  expectInterRestoreCall()
  fixture.execs.expectCalls(*setupCalls)
  callRestore("tota", "04", "--to=dest.backup")

  fixture.execs.expectCalls(*setupCalls)
  callRestore("2014", "3:")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("patterns", "ambiguous")

  fixture.execs.expectCalls(*setupCalls)
  callRestore("this-is-not-a-substring")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("patterns", "no match")

def test_shouldCallListFilesWithAnInterfaceSimilarToRestore(fixture):
  fixture.writeInterpreter("inter", """#!/usr/bin/env bash
  if [ $1 = versions-of ]; then
    echo '1970-01-01T00:00:50+00:00'
    echo 100000000
  fi
  if [[ $1 = list-files && $2 = container/folder && $3 = 2 && $5 = 50 ]]; then
    echo "F some-file"
    echo "D and-a-dir"
  fi""")
  fixture.writeRuleWithSchedAndInter(
      interpreterName="inter",
      loc1="/etc/config",
      loc2="/var/spool")

  fixture.runSibtWithRealStreamsAndExec("list-files", 
      "/var/spool/container/folder", "1970")
  fixture.stderrShouldBeEmpty()
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder("F some-file", 
      "D and-a-dir")

def test_shouldCallRunnerNamedInHashbangLineOfInterpretersIfItExists(fixture):
  runnerPath = fixture.writeRunner("faith")
  interPath = fixture.writeInterpreter("custom-inter", "#!faith")
  fixture.writeAnyScheduler("sched")
  fixture.writeAnyRule("rule", "sched", "custom-inter")

  allowAnyCallsExceptOptions = (runnerPath, lambda args: args[1] != 
      "available-options", "", {"anyNumber": True})

  fixture.execs.expectCalls((runnerPath, (interPath, "available-options"), ""),
      allowAnyCallsExceptOptions)
  fixture.runSibtCheckingExecs("list", "interpreters")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldPerformSanityChecksOnRulesBeforeSyncingExceptWhenDisabled(
    fixture):
  containerDir = fixture.tmpdir.mkdir("within")
  containerDir.mkdir("relative-dir")

  fixture.writeAnyScheduler("simple")
  fixture.writeAnyInterpreter("rsync")
  fixture.writeRuleWithSchedAndInter("backup-rule",
      schedulerName="simple",
      interpreterName="rsync",
      loc1="relative-dir")

  with containerDir.as_cwd():
    fixture.runSibt("sync", "backup-rule")
    fixture.shouldHaveExitedWithStatus(1)
    fixture.stderrShouldContain("backup-rule", "relative-dir", "not absolute")

  fixture.runSibt("--no-checks", "sync", "backup-rule")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldCheckIfTwoRulesToSyncWouldWriteToTheSameLocation(fixture):
  fixture.writeInterpreter("bidirectional", """#!/usr/bin/env bash
  if [ $1 = writes-to ]; then
    echo 1
    echo 2
  fi""")
  fixture.writeInterpreter("unidirectional", """#!/usr/bin/env bash
  if [ $1 = writes-to ]; then
    notImplementedCode=3
    exit $notImplementedCode
  fi""")
  fixture.writeRuleWithSchedAndInter("uni",
      loc1=fixture.validLocForInterpreter("src/1"),
      loc2=fixture.validLocForInterpreter("dest/1"),
      interpreterName="unidirectional")
  fixture.writeRuleWithSchedAndInter("bi", 
      loc1=fixture.validLocForInterpreter("dest/1", create=False),
      loc2=fixture.validLocForInterpreter("dest/2"),
      interpreterName="bidirectional")

  fixture.runSibtWithRealStreamsAndExec("sync", "uni", "bi")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("dest/1", "overlapping writes", "bi", "uni")

def test_shouldProvideACheckActionThatPerformsTheSameChecksAsSyncButDoesntSync(
    fixture):
  fixture.writeRuleWithSchedAndInter("valid-rule")

  fixture.runSibt("check", "valid-rule")
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(0)

  fixture.writeRuleWithSchedAndInter("invalid-rule",
      loc1="",
      loc2="")

  fixture.runSibt("check", "invalid-rule", "valid-rule")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdoutShouldContain("invalid-rule", "exist")
