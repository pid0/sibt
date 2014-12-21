from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from sibt.infrastructure.fileobjoutput import FileObjOutput
from fnmatch import fnmatchcase
from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.common.execmock import ExecMock
from py.path import local
from sibt import main
import pytest
import os.path
import sys
from test.common import mock
from test.common.mockedmoduleloader import MockedModuleLoader
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from test.common.assertutil import iterableContainsInAnyOrder, \
    iterableContainsPropertiesInAnyOrder, equalsPred
from test.common.pathsbuilder import existingPaths, pathsIn
from test.acceptance.configfolderswriter import ConfigFoldersWriter
from test.acceptance.interpreterbuilder import InterpreterBuilder
from test.acceptance.schedulerbuilder import SchedulerBuilder
from test.acceptance.rulebuilder import RuleBuilder
from test.acceptance.configscenarioconstructor import ConfigScenarioConstructor

class SibtSpecFixture(object):
  def __init__(self, tmpdir, capfd):
    self.tmpdir = tmpdir
    userDir = tmpdir / "user"
    sysDir = tmpdir / "system"
    readonlyDir = tmpdir.mkdir("usr-share")

    self.paths = existingPaths(pathsIn(userDir, readonlyDir))
    self.sysPaths = pathsIn(sysDir, "")

    self.testRuleCounter = 1
    self.setRootUserId()
    self.mockedSchedulers = dict()
    self.execs = ExecMock()
    self.capfd = capfd

    self.confFolders = ConfigFoldersWriter(self.sysPaths, self.paths, tmpdir)
    self.aScheduler = SchedulerBuilder(self.paths, self.sysPaths, 
        self.confFolders, "sched", self.mockedSchedulers, dict())
    self.anInterpreter = InterpreterBuilder(self.paths, self.sysPaths, 
        self.confFolders, "inter", self.execs, dict())
    self.aRule = RuleBuilder(self.paths, self.sysPaths, self.confFolders, 
        "rule", dict())
    self.conf = ConfigScenarioConstructor(self.confFolders, self.anInterpreter,
        self.aScheduler, self.aRule)

  def stderrShouldBeEmpty(self):
    assert self.result.stderr == ""
  def stderrShouldContain(self, *phrases):
    for phrase in phrases:
      assert phrase in self.result.stderr
  def stderrShouldNotContain(self, *phrases):
    for phrase in phrases:
      assert phrase not in self.result.stderr
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
    self.execs.reset()
    self.result = RunResult(stdout.stringBuffer, stderr.stringBuffer,
        exitStatus)

  def _runSibt(self, stdout, stderr, processRunner, arguments):
    moduleLoader = PyModuleLoader("foo") if \
        len(self.mockedSchedulers) == 0 else \
        MockedModuleLoader(self.mockedSchedulers)
    exitStatus = main.run(arguments, stdout, stderr, processRunner,
      self.paths, self.sysPaths, self.userId, moduleLoader)

    if len(self.mockedSchedulers) > 0:
      for mockedSched in self.mockedSchedulers.values():
        mockedSched.checkExpectedCalls()
    
    return exitStatus
    
@pytest.fixture
def fixture(tmpdir, capfd):
  return SibtSpecFixture(tmpdir, capfd)
    
def test_shouldInvokeTheCorrectConfiguredSchedulersAndInterpreters(fixture):
  sched = fixture.conf.aSched().withRunFuncCode("""
def run(args): print("scheduled rule '" + args[0].ruleName + "'")
    """).write()

  inter1 = fixture.conf.anInter().withBashCode("""
  if [ $1 = available-options ]; then
    echo Option
  elif [ $1 = sync ]; then  
    echo one 
  fi""").write()

  inter2 = fixture.conf.anInter().withBashCode("""
  if [ $1 = sync ]; then  
    echo two
  fi
  """).write()

  rule = fixture.conf.aRule("foo-rule").withScheduler(sched).\
      withInterpreter(inter1).withContent("""
[Interpreter]
Name = {inter}
Option=1
Loc1={loc1}
Loc2={loc2}

[Scheduler]
Name = {sched}""").write()

  ignoredRule = fixture.conf.aRule().withScheduler(sched).\
      withInterpreter(inter2).withContent("""
  [Scheduler]
  Name = {sched}
[Interpreter]
Name = {inter}
Loc1={loc1}
Loc2={loc2}
""").write()

  fixture.runSibtWithRealStreamsAndExec("sync", "foo-rule")
  fixture.stdoutShouldBe("scheduled rule 'foo-rule'\n")
      
  fixture.runSibtWithRealStreamsAndExec("sync-uncontrolled", "foo-rule")
  fixture.stdoutShouldBe("one\n")

def test_shouldBeAbleToListOnlyRootUsersConfigurationOptionsToStdout(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.writeAnyRule("rule-1", "sched-1", "inter-1")
  fixture.conf.writeAnyRule("test-rule-2", "sched-2", "inter-1")
  fixture.conf.writeAnyScheduler("sched-1")
  fixture.conf.writeAnyScheduler("sched-2")
  fixture.conf.writeAnyInterpreter("inter-1")
  fixture.conf.writeAnyInterpreter("where-is-this?", sysConfig=True)

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
  fixture.confFolders.deleteConfigAndVarFolders()
  fixture.runSibt()

  for path in [fixture.paths.rulesDir, fixture.paths.schedulersDir,
      fixture.paths.interpretersDir, fixture.paths.varDir]:
    assert os.path.isdir(path)

def test_ifInvokedAsNormalUserItShouldListSystemConfigAsWellAsTheOwn(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.writeAnyRule("normal-user-rule", "user-sched", "user-inter")
  fixture.conf.writeAnyRule("system-rule", "system-sched", "system-inter", 
      sysConfig=True)
  fixture.conf.writeAnyInterpreter("user-inter")
  fixture.conf.writeAnyInterpreter("system-inter", sysConfig=True)
  fixture.conf.writeAnyScheduler("user-sched")
  fixture.conf.writeAnyScheduler("system-sched", sysConfig=True)

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
  fixture.conf.aRule("suspect-rule").withContent("sdafsdaf").write()
  fixture.conf.ruleWithSchedAndInter("some-valid-rule").write()

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("invalid", "suspect-rule")

def test_shouldDistinguishBetweenDisabledAndSymlinkedToEnabledRules(fixture):
  fixture.conf.ruleWithSchedAndInter("is-on").enabled().write()
  fixture.conf.ruleWithSchedAndInter("is-off").write()

  fixture.runSibt("list", "rules")
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
      "*is-on*enabled*",
      "*is-off*disabled*")

def test_shouldFailIfConfiguredSchedulerOrInterpreterDoesNotExist(fixture):
  fixture.conf.ruleWithSched("invalid-rule").\
      withInterpreterName("is-not-there").write()
  fixture.conf.ruleWithSchedAndInter("valid-rule").write()

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("interpreter", "is-not-there", "not found")

def test_shouldPassOptionsAsIsToCorrectSchedulersAndInterpreters(fixture):
  inter = fixture.conf.anInter().allowingSetupCallsExceptOptions().\
      withTestOptions().write()
  schedMock, sched = fixture.conf.aSched().withTestOptions().mock()

  rule = fixture.conf.aRule().\
      withSchedOpts(Interval="2w").\
      withInterOpts(AddFlags="-X -A").\
      withScheduler(sched).\
      withInterpreter(inter).write()

  schedMock.expectCallsInAnyOrder(mock.callMatching("run", lambda schedulings:
      len(schedulings) == 1 and
      schedulings[0].ruleName == rule.name and 
      schedulings[0].options == { "Interval": "2w" }))

  fixture.runSibtCheckingExecs("sync", rule.name)

  inter.expecting((lambda args: args[0] == "sync" and 
    set(args[1:]) == {"AddFlags=-X -A", "Loc1=" + rule.loc1, 
      "Loc2=" + rule.loc2}, "")).reMakeExpectations()
  fixture.runSibtCheckingExecs("sync-uncontrolled", rule.name)

def test_shouldFailIfOptionsAreUsedNotPredefinedOrSupportedByConfiguration(
    fixture):
  sched = fixture.conf.aSched().withTestOptions().write()
  inter = fixture.conf.anInter().withTestOptionsCode().write()

  fixture.conf.aRule().withScheduler(sched).withInterpreter(inter).\
      withInterOpts(AddFlags="foo", DoesNotExist="abc").\
      withSchedOpts(Interval="bar").write()

  fixture.runSibtWithRealStreamsAndExec()
  fixture.stdoutShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("unsupported", "options", "DoesNotExist")
  fixture.stderrShouldNotContain("AddFlags", "Interval")

def test_shouldIssureErrorMessageIfRuleNameContainsAComma(fixture):
  fixture.conf.ruleWithSchedAndInter("no,comma").write()

  fixture.runSibt()
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldContain("invalid character", "no,comma")
def test_shouldIssureErrorMessageIfRuleNameContainsAnAt(fixture):
  fixture.conf.ruleWithSchedAndInter("no@at").write()

  fixture.runSibt()
  fixture.stderrShouldContain("invalid character")
def test_shouldIssureErrorMessageIfRuleNameContainsASpace(fixture):
  fixture.conf.ruleWithSchedAndInter("no space").write()

  fixture.runSibt()
  fixture.stderrShouldContain("invalid character", "no space")

def test_shouldInitSchedulersCorrectlyIncludingSibtInvocationWithGlobalOpts(
    fixture):
  fixture.conf.aSched().withInitFuncCode(
"""def init(sibtInvocation, paths): print("{0},{1}".format(
" ".join(sibtInvocation), paths.configDir))""").write()

  newReadonlyDir = str(fixture.tmpdir)

  fixture.runSibtWithRealStreamsAndExec("--readonly-dir", newReadonlyDir, 
      "list", "schedulers")
  fixture.stdoutShouldContain("{0} --readonly-dir {1}".format(sys.argv[0],
      newReadonlyDir) + "," +
      fixture.paths.configDir + "\n")

def test_shouldBeAbleToMatchRuleNameArgsAgainstListOfEnabledRulesAndRunThemAll(
    fixture):
  schedMock, sched = fixture.conf.aSched().mock()

  disabledRule = fixture.conf.aRule().withScheduler(sched).\
      withInterpreter(fixture.conf.anInter().write())
  enabledRule = disabledRule.enabled()

  for name in ["rule-a1", "rule-a2", "rule-b"]:
    enabledRule.withName(name).write()
  for name in ["disabled-1", "disabled-2"]:
    disabledRule.withName(name).write()

  schedMock.expectCallsInAnyOrder(mock.callMatching("run", lambda schedulings:
      iterableContainsPropertiesInAnyOrder(schedulings, 
        lambda scheduling: scheduling.ruleName,
        equalsPred("rule-a1"), equalsPred("rule-a2"), 
        equalsPred("disabled-2"))))

  fixture.runSibt("sync", "*a[0-9]", "disabled-2")

def test_shouldExitWithErrorMessageIfNoRuleNamePatternMatches(fixture):
  fixture.conf.ruleWithSchedAndInter("rule").write()

  fixture.runSibt("sync", "foo")
  fixture.stderrShouldContain("no matching rule", "foo")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldIgnoreSysRulesWhenSyncing(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.ruleWithSchedAndInter("sys-rule", isSysConfig=True).write()

  fixture.setNormalUserId()

  fixture.runSibt("sync", "sys-rule")
  fixture.stderrShouldContain("no matching", "sys-rule")

def test_shouldSupportCommandLineOptionToCompletelyIgnoreSysConfig(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.aSched("own-sched").write()
  sched = fixture.conf.aSysSched().withName("systemd").write()
  inter = fixture.conf.aSysInter().withName("tar").write()
  fixture.conf.aSysRule().withName("os-backup").\
      withScheduler(sched).withInterpreter(inter).write()

  fixture.setNormalUserId()

  fixture.runSibt("--no-sys-config", "list")
  fixture.stdoutShouldContain("own-sched")
  fixture.stdoutShouldNotContain("systemd", "tar", "os-backup")

def test_shouldAdditionallyReadInterpretersAndSchedulersFromReadonlyDir(
    fixture):
  fixture.confFolders.createReadonlyFolders()

  fixture.conf.aSched("included-scheduler").write(toReadonlyDir=True)
  fixture.conf.anInter("included-interpreter").write(
      toReadonlyDir=True)

  fixture.runSibt()
  fixture.stdoutShouldContainLinePatterns(
      "*included-interpreter*", "*included-scheduler*")

def test_shouldBeAbleToOverrideDefaultPathsWithCommandLineOptions(fixture):
  newConfigDir = fixture.tmpdir.mkdir("foo")
  newSchedulersDir = newConfigDir.mkdir("schedulers")
  newSchedulersDir.join("jct-scheduler").write(
      fixture.conf.aSched().content)

  fixture.runSibt("--config-dir=" + str(newConfigDir), "list", "schedulers")
  fixture.stdoutShouldContain("jct-scheduler")

def test_shouldConsiderNameLoc1AndLoc2AsMinimumAndAlreadyAvailableOptions(
    fixture):
  fixture.conf.ruleWithSchedAndInter("invalid-rule").withContent(
      """[Interpreter]
      Name={inter}
      [Scheduler]
      Name={sched}""").write()

  fixture.runSibt()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("invalid-rule", "minimum", "Loc1")

def test_shouldProvideAWayToImportRuleConfigsAndANamingSchemeForIncludeFiles(
    fixture):
  sched = fixture.conf.aSched().withTestOptions().write()

  fixture.conf.ruleWithInter("header.inc").withScheduler(sched).\
      withContent("""
[Scheduler]
Name = {sched}
Interval = 3w
[Interpreter]
Name = {inter}
""").write()

  fixture.conf.aRule("actual-rule").withContent("""
#import header
[Interpreter]
Loc1={loc1}
Loc2={loc2}
[Scheduler]
Syslog = yes""").write()

  fixture.runSibt("show", "actual-rule")
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
  schedMock, errorSched = fixture.conf.aSched().\
      withName("uncontent-sched").mock()
  schedMock.check = lambda schedulings: ["this problem cannot be solved"] if \
      len(schedulings) == 2 else []

  _, permissiveSched = fixture.conf.aSched("content-sched").mock()

  enabledRule = fixture.conf.ruleWithInter().enabled()
  enabledRule.withName("badly-confd-rule").withScheduler(errorSched).write()
  enabledRule.withName("another-bad-rule").withScheduler(errorSched).write()
  enabledRule.withName("correctly-confd-rule").withScheduler(permissiveSched).\
      write()

  fixture.runSibt("sync", "*")
  fixture.stderrShouldContain(" in ", "badly-confd-rule", 
      "another-bad-rule", "this problem cannot be solved")
  fixture.shouldHaveExitedWithStatus(1)

  errorSched.reRegister(schedMock)
  permissiveSched.mock()
  fixture.runSibt("sync", "correctl*", "badly*")
  fixture.stderrShouldNotContain("correctly-confd")

def test_shouldFailAndPrintErrorIfInterpreterReturnsNonZero(fixture):
  inter = fixture.conf.anInter("failing-inter").withBashCode("exit 1").write()
  fixture.conf.ruleWithSched().withInterpreter(inter).write()

  fixture.runSibtWithRealStreamsAndExec()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldContain("failing-inter", "error", "calling")

def test_shouldCollectVersionsOfAFileFromRulesThatHaveItWithinLoc1OrLoc2(
    fixture):
  fixture.confFolders.createSysFolders()

  utcThirdOfMarch = "2014-01-03T18:35:00"
  utcMarch3rdInDifferentZone = "2014-01-03T20:35:00+02:00"
  utc123 = "1970-01-01T00:02:03"
  utc0 = "1970-01-01T00:00:00"

  testDir = fixture.tmpdir.mkdir("versions-test")
  dataDir = str(testDir) + "/home/foo/data"
  backupDir = str(testDir) + "/mnt/backup/data"
  fileName = "folder/some-file"
  fileInDataDir = os.path.join(dataDir, fileName)

  inter = fixture.conf.interReturningVersions(
      forRelativeFile=fileName,
      ifWithinLoc1=[utcMarch3rdInDifferentZone, "0"],
      ifWithinLoc2=["123"]).asSysConfig().write()

  baseRule = fixture.conf.ruleWithSched().withInterpreter(inter)
  baseRule.withName("rule-1").\
      withLoc1(dataDir).\
      withLoc2(backupDir).asSysConfig().write()
  baseRule.withName("rule-2").\
      withLoc1(backupDir).\
      withLoc2(str(testDir) + "/mnt/remote").write()

  fixture.setNormalUserId()

  fixture.tmpdir.join("link").mksymlinkto(fileInDataDir)
  with fixture.tmpdir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of", 
        "link")
    fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
        "*rule-1," + utcThirdOfMarch + "*",
        "*rule-1," + utc0 + "*")

  with testDir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of",
        "mnt/backup/data/" + fileName)
    fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder(
        "*rule-1," + utc123 + "*",
        "*rule-2," + utcThirdOfMarch + "*",
        "*rule-2," + utc0 + "*")

def test_shouldCorrectlyCallRestoreForTheVersionThatHasAllGivenSubstrings(
    fixture):
  def callRestore(*args):
    fixture.runSibtCheckingExecs("--utc", "restore", *args)

  dataDir = "/mnt/data/"
  backupDir = "/mnt/backup/"
  fileName = "file-to-restore"
  inter = fixture.conf.anInter().allowingSetupCalls()
  baseRule = fixture.conf.ruleWithSched().withInterpreter(inter).\
      withLoc1(dataDir)
  baseRule.withName("total-backup").withLoc2(backupDir).write()
  baseRule.withName("other-rule").withLoc2("/mnt/quux").write()

  april5th = "2014-04-05T13:35:34+00:00"
  march3rd = "2014-03-30T21:43:12+00:00"
  april5thTimestamp = "1396704934"

  inter = inter.allowing((lambda args: args[0] == "versions-of",
    "\n".join([april5th, march3rd]))).write()

  callRestore(dataDir + fileName, "2014", "3:")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("patterns", "ambiguous")

  inter.reMakeExpectations()
  callRestore(dataDir + fileName, "this-is-not-a-substring")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("patterns", "no match")

  inter.expecting((lambda args: args[0] == "restore" and 
    "Loc2=" + backupDir in args and 
    args[1:6] == (fileName, "1", april5th, april5thTimestamp, "dest.backup"),
    "")).reMakeExpectations()
  callRestore(dataDir + fileName, "tota", "04", "--to=dest.backup")

def test_shouldCallListFilesWithAnInterfaceSimilarToRestore(fixture):
  inter = fixture.conf.anInter().withBashCode("""
  if [ $1 = versions-of ]; then
    echo '1970-01-01T00:00:50+00:00'
    echo 100000000
  fi
  if [[ $1 = list-files && $2 = container/folder && $3 = 2 && $5 = 50 ]]; then
    echo "F some-file"
    echo "D and-a-dir"
  fi""").write()
  fixture.conf.ruleWithSched().withInterpreter(inter).\
      withLoc2("/var/spool").write()

  fixture.runSibtWithRealStreamsAndExec("list-files", 
      "/var/spool/container/folder", "1970")
  fixture.stderrShouldBeEmpty()
  fixture.stdoutShouldExactlyContainLinePatternsInAnyOrder("F some-file", 
      "D and-a-dir")

def test_shouldCallRunnerNamedInHashbangLineOfInterpretersIfItExists(fixture):
  runnerPath = fixture.confFolders.writeRunner("faith")
  inter = fixture.conf.anInter().withCode("#!faith").write()
  fixture.conf.ruleWithSched().withInterpreter(inter).write()

  allowAnyCallsExceptOptions = (runnerPath, lambda args: args[1] != 
      "available-options", "", {"anyNumber": True})

  fixture.execs.expectCalls(
      (runnerPath, (str(inter.path), "available-options"), ""),
      allowAnyCallsExceptOptions)
  fixture.runSibtCheckingExecs("list", "interpreters")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldPerformSanityChecksOnRulesBeforeSyncingExceptWhenDisabled(
    fixture):
  containerDir = fixture.tmpdir.mkdir("shell")
  containerDir.mkdir("relative-dir")

  fixture.conf.ruleWithSchedAndInter("relative-rule").\
      withLoc1("relative-dir").write()

  with containerDir.as_cwd():
    fixture.runSibt("sync", "relative-rule")
    fixture.shouldHaveExitedWithStatus(1)
    fixture.stderrShouldContain("relative-rule", "relative-dir", "not absolute")

  fixture.runSibt("sync", "relative-rule")
  fixture.stderrShouldContain("not exist")
  fixture.shouldHaveExitedWithStatus(1)

  fixture.runSibt("--no-checks", "sync", "relative-rule")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldCheckIfTwoRulesToSyncWouldWriteToTheSameLocation(fixture):
  bidirectional = fixture.conf.anInter().withBashCode("""
  if [ $1 = writes-to ]; then
    echo 1
    echo 2
  fi""").write()
  unidirectional = fixture.conf.anInter().withBashCode("""
  if [ $1 = writes-to ]; then
    notImplementedCode=3
    exit $notImplementedCode
  fi""").write()

  fixture.conf.ruleWithSched("uni").withInterpreter(unidirectional).\
      withLoc1(fixture.confFolders.validInterpreterLoc("src/1")).\
      withLoc2(fixture.confFolders.validInterpreterLoc("dest/1")).write()
  fixture.conf.ruleWithSched("bi").withInterpreter(bidirectional).\
      withLoc1(fixture.confFolders.validInterpreterLoc("dest/1")).\
      withLoc2(fixture.confFolders.validInterpreterLoc("dest/2")).write()

  fixture.runSibtWithRealStreamsAndExec("sync", "uni", "bi")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderrShouldContain("dest/1", "overlapping writes", "bi", "uni")

def test_shouldProvideACheckActionThatPerformsTheSameChecksAsSyncButDoesntSync(
    fixture):
  fixture.conf.ruleWithSchedAndInter("valid-rule").write()

  fixture.runSibt("check", "valid-rule")
  fixture.stdoutShouldBeEmpty()
  fixture.stderrShouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(0)

  fixture.conf.ruleWithEmptyLocs("invalid-rule").write()

  fixture.runSibt("check", "invalid-rule", "valid-rule")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdoutShouldContain("invalid-rule", "not exist")
