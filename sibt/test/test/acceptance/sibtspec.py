from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
import shutil
from fnmatch import fnmatchcase
from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.common.interceptingoutput import InterceptingOutput
from test.common.execmock import ExecMock
from py._path.local import LocalPath
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

  def _writeRule(self, paths, name, contents):
    LocalPath(paths.rulesDir).join(name).write(contents)
  def writeSysRule(self, name, contents):
    self._writeRule(self.sysPaths, name, contents)
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

  def writeRunner(self, name):
    os.makedirs(self.paths.runnersDir)
    runnerPath = LocalPath(self.paths.runnersDir).join(name)
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
  
  def stderrShouldBeEmpty(self):
    assert self.result.stderr.stringBuffer == ""
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
  def stdoutShouldNotContain(self, *notExpectedPhrases):
    for phrase in notExpectedPhrases:
      assert phrase.lower() not in self.result.stdout.stringBuffer.lower()

  def shouldHaveExitedWithStatus(self, expectedStatus):
    assert self.result.exitStatus == expectedStatus
    
  def setNormalUserId(self):
    self.userId = 25
  def setRootUserId(self):
    self.userId = 0
  
  def runSibtWithRealStreamsAndExec(self, *arguments):
    with InterceptingOutput.stdout() as stdout, \
        InterceptingOutput.stderr() as stderr:
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
      self.paths, self.sysPaths, self.userId, schedulerLoader)
    
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
echo foo >&2
exit 1""")
  fixture.writeAnyRule("rule", "sched", "failing-inter")

  fixture.runSibtWithRealStreamsAndExec()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldContain("failing-inter", "failed")

def test_shouldCollectVersionsOfAFileFromRulesThatHaveItWithinLoc1OrLoc2(
    fixture):
  fixture.createSysConfigFolders()
  fixture.setNormalUserId()

  testDir = fixture.tmpdir.mkdir("versions-test")

  fixture.writeInterpreter("has-different-versions-for-locs", 
"""#!/usr/bin/env bash
if [[ $1 = versions-of && $2 = folder/some-file ]]; then
  relativeToLoc=$3
  if [ $relativeToLoc = 1 ]; then
    echo '2014-01-03T20:35:00+02:00'
    echo '0'
  fi
  if [ $relativeToLoc = 2 ]; then
    echo 123
  fi
fi""")

  fixture.writeAnyScheduler("sched")
  fixture.writeSysRule("rule-1", """
  [Scheduler]
  Name = sched
  [Interpreter]
  Name = has-different-versions-for-locs
  Loc1 = {0}/home/foo/data
  Loc2 = {0}/mnt/backup/data""".format(testDir))
  fixture.writeRule("rule-2", """
  [Scheduler]
  Name = sched
  [Interpreter]
  Name = has-different-versions-for-locs
  Loc1 = {0}/mnt/backup/data/
  Loc2 = {0}/mnt/remote""".format(testDir))

  utcThirdOfMarch = "2014-01-03T18:35:00"
  utc123 = "1970-01-01T00:02:03"
  utc0 = "1970-01-01T00:00:00"

  symlink = fixture.tmpdir.join("link")
  symlink.mksymlinkto(
      "{0}/home/foo/data/folder/some-file".format(testDir))
  fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of", 
      str(symlink))
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

  optionsCall = (interPath, lambda args: args[0] == "available-options", "")
  def versionsOfCall(loc2):
    return (interPath, lambda args: args[0] == "versions-of" and 
      "Loc2=" + loc2 in args and args[1:3] == ("foo", "1"), "\n".join([
      april5th, march3th]))
  setupCalls = (optionsCall, optionsCall, versionsOfCall("/mnt/backup"),
      versionsOfCall("/mnt/quux"))

  fixture.execs.expectMatchingCalls(
      (interPath, lambda args: args[0] == "restore" and 
      "Loc2=/mnt/backup" in args and args[1:6] == ("foo", "1", april5th, 
          april5thTimestamp, "dest.backup"), ""), *setupCalls, anyOrder=True)
  fixture.runSibtCheckingExecs("--utc", "restore", "/mnt/data/foo",
      "tota", "04", "--to=dest.backup")

  fixture.execs.expectMatchingCalls(*setupCalls, anyOrder=True)
  fixture.runSibtCheckingExecs("--utc", "restore", "/mnt/data/foo",
      "2014", "3:")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("patterns", "ambiguous")

  fixture.execs.expectMatchingCalls(*setupCalls, anyOrder=True)
  fixture.runSibtCheckingExecs("--utc", "restore", "/mnt/data/foo",
      "this-is-not-a-substring")
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
  fixture.writeAnyScheduler("sched")
  fixture.writeRule("my-rule", """
  [Scheduler]
  Name = sched
  [Interpreter]
  Name = inter
  Loc1 = /etc/config
  Loc2 = /var/spool""")

  fixture.runSibtWithRealStreamsAndExec("list-files", 
      "/var/spool/container/folder", "1970")
  fixture.stderrShouldBeEmpty()
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder("F some-file", 
      "D and-a-dir")


def test_shouldCallRunnerNamedInHashbangLineOfInterpretersIfItExists(fixture):
  runnerPath = fixture.writeRunner("faith")
  interPath = fixture.writeInterpreter("custom-inter", """#!faith
  echo foo""")
  fixture.writeAnyScheduler("sched")
  fixture.writeAnyRule("rule", "sched", "custom-inter")

  fixture.execs.expectCalls((runnerPath, (interPath, "available-options"), ""))
  fixture.runSibtCheckingExecs("list", "interpreters")
  fixture.shouldHaveExitedWithStatus(0)


