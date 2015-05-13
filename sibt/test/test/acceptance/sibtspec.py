from sibt.infrastructure.coprocessrunner import CoprocessRunner
from sibt.infrastructure.fileobjoutput import FileObjOutput
from fnmatch import fnmatchcase
from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.common.execmock import ExecMock
from test.common import execmock
from py.path import local
from sibt import main
import pytest
import os.path
import sys
from test.common import mock
from test.common.mockedmoduleloader import MockedModuleLoader
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from test.common.assertutil import iterableContainsInAnyOrder, \
    iterableContainsPropertiesInAnyOrder, equalsPred, strToTest, iterToTest, \
    FakeException
from test.common.pathsbuilder import existingPaths, pathsIn
from test.acceptance.configfolderswriter import ConfigFoldersWriter
from test.acceptance.synchronizerbuilder import SynchronizerBuilder
from test.acceptance.schedulerbuilder import SchedulerBuilder
from test.acceptance.rulebuilder import RuleBuilder
from test.acceptance.configscenarioconstructor import ConfigScenarioConstructor

Utc0 = "1970-01-01T00:00:00"

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
    self.aSyncerpreter = SynchronizerBuilder(self.paths, self.sysPaths,
        self.confFolders, "syncer", self.execs, dict())
    self.aRule = RuleBuilder(self.paths, self.sysPaths, self.confFolders,
        "rule", dict())
    self.conf = ConfigScenarioConstructor(self.confFolders, self.aSyncerpreter,
        self.aScheduler, self.aRule)

  @property
  def stdout(self):
    return self.result.stdout
  @property
  def stderr(self):
    return self.result.stderr

  def shouldHaveExitedWithStatus(self, expectedStatus):
    assert self.result.exitStatus == expectedStatus

  def setNormalUserId(self):
    self.userId = 25
  def setRootUserId(self):
    self.userId = 0

  def runSibtWithRealStreamsAndExec(self, *arguments):
    exitStatus = 1
    try:
      exitStatus = self._runSibt(FileObjOutput(sys.stdout),
          FileObjOutput(sys.stderr), CoprocessRunner(), arguments)
    finally:
      stdout, stderr = self.capfd.readouterr()
      self.result = RunResult(strToTest(stdout), strToTest(stderr), exitStatus)

  def runSibtCheckingExecs(self, *arguments):
    self.execs.returningNotImplementedStatuses = False
    self._runSibtMockingExecAndStreams(self.execs, arguments)

  def runSibt(self, *arguments):
    self.execs.returningNotImplementedStatuses = True
    self._runSibtMockingExecAndStreams(self.execs, arguments)

  def _runSibtMockingExecAndStreams(self, execs, arguments):
    stdout = BufferingOutput()
    stderr = BufferingOutput()
    exitStatus = 1
    try:
      exitStatus = self._runSibt(stdout, stderr, self.execs, arguments)
    finally:
      self.result = RunResult(strToTest(stdout.stringBuffer),
          strToTest(stderr.stringBuffer), exitStatus)
    try:
      self.execs.check()
    except:
      print(stderr.stringBuffer)
      raise
    self.execs.reset()

  def _runSibt(self, stdout, stderr, processRunner, arguments):
    moduleLoader = PyModuleLoader("foo") if \
        len(self.mockedSchedulers) == 0 else \
        MockedModuleLoader(self.mockedSchedulers)
    exitStatus = main.run(arguments, stdout, stderr, processRunner,
      self.paths, self.sysPaths, self.userId, moduleLoader)

    if len(self.mockedSchedulers) > 0:
      try:
        for mockedSched in self.mockedSchedulers.values():
          mockedSched.checkExpectedCalls()
      except:
        print(stderr.stringBuffer)
        raise

    return exitStatus

@pytest.fixture
def fixture(tmpdir, capfd):
  return SibtSpecFixture(tmpdir, capfd)

def test_shouldInvokeTheCorrectConfiguredSchedulersAndSynchronizers(fixture):
  sched = fixture.conf.aSched().withRunFuncCode("""
def run(args): print("scheduled rule '" + args[0].ruleName + "'")
    """).write()

  syncer1 = fixture.conf.aSyncer().withBashCode("""
  if [ $1 = available-options ]; then
    echo Option
  elif [ $1 = sync ]; then
    echo one
  else exit 200; fi""").write()

  syncer2 = fixture.conf.aSyncer().withBashCode("""
  if [ $1 = sync ]; then
    echo two
  else exit 200; fi""").write()

  rule = fixture.conf.aRule("foo-rule").withScheduler(sched).\
      withSynchronizer(syncer1).withContent("""
[Synchronizer]
Name = {syncer}
Option=1
Loc1={loc1}
Loc2={loc2}

[Scheduler]
Name = {sched}""").write()

  ignoredRule = fixture.conf.aRule().withScheduler(sched).\
      withSynchronizer(syncer2).withContent("""
  [Scheduler]
  Name = {sched}
[Synchronizer]
Name = {syncer}
Loc1={loc1}
Loc2={loc2}
""").write()

  fixture.runSibtWithRealStreamsAndExec("schedule", "foo-rule")
  fixture.stdout.shouldBe("scheduled rule 'foo-rule'\n")

  fixture.runSibtWithRealStreamsAndExec("sync-uncontrolled", "foo-rule")
  fixture.stdout.shouldBe("one\n")

def test_shouldBeAbleToListOnlyRootUsersConfigurationOptionsToStdout(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.writeAnyRule("rule-1", "sched-1", "syncer-1")
  fixture.conf.writeAnyRule("test-rule-2", "sched-2", "syncer-1")
  fixture.conf.writeAnyScheduler("sched-1")
  fixture.conf.writeAnyScheduler("sched-2")
  fixture.conf.writeAnySynchronizer("syncer-1")
  fixture.conf.writeAnySynchronizer("where-is-this?", sysConfig=True)

  fixture.setRootUserId()

  fixture.runSibt("list", "synchronizers")
  fixture.stdout.shouldContainLinePatterns("*syncer-1*")

  fixture.runSibt("list", "schedulers")
  fixture.stdout.shouldContainLinePatterns("*sched-1*", 
      "*sched-2*")

  fixture.runSibt("list", "rules")
  fixture.stdout.shouldContainLinePatterns("*rule-1*", 
      "*test-rule-2*")

  fixture.runSibt("list")
  fixture.stdout.shouldIncludeInOrder("synchronizers", "syncer-1")
  fixture.stdout.shouldInclude("rule-1", "test-rule-2", "sched-1", "sched-2")

def test_shouldAutomaticallyCreateFoldersIfTheyDontExist(fixture):
  fixture.confFolders.deleteConfigAndVarFolders()
  fixture.runSibt()

  for path in [fixture.paths.rulesDir, fixture.paths.schedulersDir,
      fixture.paths.synchronizersDir, fixture.paths.varDir]:
    assert os.path.isdir(path)

def test_ifInvokedAsNormalUserItShouldListSystemConfigAsWellAsTheOwn(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.writeAnyRule("normal-user-rule", "user-sched", "user-syncer")
  fixture.conf.writeAnyRule("system-rule", "system-sched", "system-syncer", 
      sysConfig=True)
  fixture.conf.writeAnySynchronizer("user-syncer")
  fixture.conf.writeAnySynchronizer("system-syncer", sysConfig=True)
  fixture.conf.writeAnyScheduler("user-sched")
  fixture.conf.writeAnyScheduler("system-sched", sysConfig=True)

  fixture.setNormalUserId()
  fixture.runSibt()
  fixture.stdout.shouldIncludeLinePatterns(
      "*normal-user-rule*",
      "+*system-rule*",
      "*user-syncer*",
      "*system-syncer*",
      "*user-sched*",
      "*system-sched*")

def test_shouldExitWithErrorMessageIfInvalidSyntaxIsFound(fixture):
  fixture.conf.aRule("suspect-rule").withContent("sdafsdaf").write()
  fixture.conf.ruleWithSchedAndSyncer("some-valid-rule").write()

  fixture.runSibt()
  fixture.stdout.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("wrong syntax", "suspect-rule")

def test_shouldDistinguishBetweenDisabledRulesAndEnabledOnesWithAnInstanceFile(
    fixture):
  rule = fixture.conf.ruleWithSchedAndSyncer("is-on").\
      enabled().\
      enabled(instanceName="foo").write()
  fixture.conf.ruleWithSchedAndSyncer("is-off").write()

  fixture.runSibt("list", "rules")
  fixture.stdout.shouldContainLinePatterns(
      "*is-on*enabled*",
      "*foo@is-on*enabled*",
      "*is-off*disabled*")

def test_shouldFailIfConfiguredSchedulerOrSynchronizerDoesNotExist(fixture):
  fixture.conf.ruleWithSched("invalid-rule").\
      withSynchronizerName("is-not-there").write()
  fixture.conf.ruleWithSchedAndSyncer("valid-rule").write()

  fixture.runSibt()
  fixture.stdout.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("synchronizer", "is-not-there", "not found")

def test_shouldPassOptionsAsIsToCorrectSchedulersAndSynchronizers(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCallsExceptOptions().\
      withTestOptions().write()
  schedMock, sched = fixture.conf.aSched().withTestOptions().mock()

  rule = fixture.conf.aRule().\
      withSchedOpts(Interval="2w").\
      withSyncerOpts(AddFlags="-X -A").\
      withScheduler(sched).\
      withSynchronizer(syncer).write()

  schedMock.expectCallsInAnyOrder(mock.callMatching("run", lambda schedulings:
      len(schedulings) == 1 and
      schedulings[0].ruleName == rule.name and
      schedulings[0].options == { "Interval": "2w" }))

  fixture.runSibtCheckingExecs("schedule", rule.name)

  syncer.expecting(execmock.call(lambda args: args[0] == "sync" and
    set(args[1:]) == {"AddFlags=-X -A", "Loc1=" + rule.loc1,
      "Loc2=" + rule.loc2, "Loc1Protocol=file", "Loc1Path=" + rule.loc1,
      "Loc2Protocol=file", "Loc2Path=" + rule.loc2})).reMakeExpectations()
  fixture.runSibtCheckingExecs("sync-uncontrolled", rule.name)

def test_shouldFailIfOptionsAreUsedNotPredefinedOrSupportedByConfiguration(
    fixture):
  sched = fixture.conf.aSched().withTestOptions().write()
  syncer = fixture.conf.aSyncer().withTestOptionsCode().write()

  fixture.conf.aRule().withScheduler(sched).withSynchronizer(syncer).\
      withSyncerOpts(AddFlags="foo", DoesNotExist="abc").\
      withSchedOpts(Interval="bar").write()

  fixture.runSibtWithRealStreamsAndExec()
  fixture.stdout.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("unsupported", "options", "DoesNotExist")
  fixture.stderr.shouldNotInclude("AddFlags", "Interval")

def test_shouldConsiderNameAndLocsAsMinimumAndAlreadyAvailableOptions(
    fixture):
  fixture.conf.ruleWithSchedAndSyncer("invalid-rule").withContent(
      """[Synchronizer]
      Name={syncer}
      [Scheduler]
      Name={sched}""").write()

  fixture.runSibt()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("invalid-rule", "minimum", "Loc1")

def test_shouldIssureErrorMessageIfARuleFileNameContainsAComma(fixture):
  fixture.conf.ruleWithSchedAndSyncer("comma").enabled(
      instanceName="no,").write()

  fixture.runSibt()
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldInclude("invalid character", "no,@comma")
def test_shouldIssureErrorMessageIfARuleFileNameContainsASpace(fixture):
  fixture.conf.ruleWithSchedAndSyncer("no space").write()

  fixture.runSibt()
  fixture.stderr.shouldInclude("invalid character", "no space")
def test_shouldIssureErrorMessageIfARuleFileNameBeginsWithAPlus(fixture):
  fixture.conf.ruleWithSchedAndSyncer("-+").write()

  fixture.runSibt()
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldBeEmpty()

  fixture.conf.ruleWithSchedAndSyncer("+-").write()
  fixture.runSibt()
  fixture.stderr.shouldInclude("at the beginning", "+-")

def test_shouldFailWhenReadingARuleConfiguredWithARelativeLocPath(fixture):
  fixture.conf.ruleWithSchedAndSyncer().withLoc1("this-is-relative").write()

  fixture.runSibt()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("this-is-relative", "not absolute")

def test_shouldInitSchedulersCorrectlyIncludingSibtInvocationWithGlobalOpts(
    fixture):
  fixture.conf.aSched().withInitFuncCode(
"""def init(sibtInvocation, paths): print("{0},{1}".format(
" ".join(sibtInvocation), paths.configDir))""").write()

  newReadonlyDir = str(fixture.tmpdir)

  fixture.runSibtWithRealStreamsAndExec("--readonly-dir", newReadonlyDir,
      "list", "schedulers")
  fixture.stdout.shouldInclude("{0} --readonly-dir {1}".format(sys.argv[0],
      newReadonlyDir) + "," +
      fixture.paths.configDir + "\n")

def test_shouldBeAbleToMatchRuleNameArgsAgainstListOfEnabledRulesAndRunThemAll(
    fixture):
  schedMock, sched = fixture.conf.aSched().mock()

  disabledRule = fixture.conf.aRule().withScheduler(sched).\
      withSynchronizer(fixture.conf.aSyncer().write())
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

  fixture.runSibt("schedule", "*a[0-9]", "disabled-2")

def test_shouldExitWithErrorMessageIfNoRuleNamePatternMatches(fixture):
  fixture.conf.ruleWithSchedAndSyncer("rule").write()

  fixture.runSibt("schedule", "foo")
  fixture.stderr.shouldInclude("no rule matching", "foo")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldRequireAnExactRuleNameMatchWhenSyncingUncontrolledly(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCalls()
  rule = fixture.conf.ruleWithSched("[rule]a*b").withSynchronizer(syncer).\
    enabled().write()

  syncer.expecting(execmock.call(lambda args: args[0] == "sync")).write()
  fixture.runSibtCheckingExecs("sync-uncontrolled", rule.name)

  syncer.reMakeExpectations()
  fixture.runSibtCheckingExecs("sync-uncontrolled", "*")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("no rule")

def test_shouldDistinguishSysRulesFromNormalRulesByPuttingAPlusInFront(fixture):
  fixture.confFolders.createSysFolders()
  fixture.setNormalUserId()

  fixture.conf.ruleWithSchedAndSyncer("system-wide", isSysConfig=True).\
      withLoc1("/boot/grub").write()

  fixture.runSibt("show", "+system-wide")
  fixture.stdout.shouldInclude("/boot/grub", "+system-wide")

def test_shouldIgnoreSysRulesWhenSchedulingAndSyncing(fixture):
  fixture.confFolders.createSysFolders()
  fixture.setNormalUserId()

  fixture.conf.ruleWithSchedAndSyncer("sys-rule", isSysConfig=True).write()

  fixture.runSibt("schedule", "*sys-rule")
  fixture.stderr.shouldInclude("no rule", "sys-rule")

  fixture.runSibt("sync-uncontrolled", "+sys-rule")
  fixture.stderr.shouldInclude("no rule", "sys-rule")

def test_shouldSupportCommandLineOptionToCompletelyIgnoreSysConfig(fixture):
  fixture.confFolders.createSysFolders()

  fixture.conf.aSched("own-sched").write()
  sched = fixture.conf.aSysSched().withName("systemd").write()
  syncer = fixture.conf.aSysSyncer().withName("tar").write()
  fixture.conf.aSysRule().withName("os-backup").\
      withScheduler(sched).withSynchronizer(syncer).write()

  fixture.setNormalUserId()

  fixture.runSibt("--no-sys-config", "list")
  fixture.stdout.shouldInclude("own-sched")
  fixture.stdout.shouldNotInclude("systemd", "tar", "os-backup")

def test_shouldAdditionallyReadSynchronizersAndSchedulersFromReadonlyDir(
    fixture):
  fixture.confFolders.createReadonlyFolders()

  fixture.conf.aSched("included-scheduler").write(toReadonlyDir=True)
  fixture.conf.aSyncer("included-synchronizer").write(
      toReadonlyDir=True)

  fixture.runSibt()
  fixture.stdout.shouldIncludeLinePatterns(
      "*included-synchronizer*", "*included-scheduler*")

def test_shouldBeAbleToOverrideDefaultPathsWithCommandLineOptions(fixture):
  newConfigDir = fixture.tmpdir.mkdir("foo")
  newSchedulersDir = newConfigDir.mkdir("schedulers")
  newSchedulersDir.join("jct-scheduler").write(
      fixture.conf.aSched().content)

  fixture.runSibt("--config-dir=" + str(newConfigDir), "list", "schedulers")
  fixture.stdout.shouldInclude("jct-scheduler")

def test_shouldProvideAWayToImportRuleConfigsAndANamingSchemeForIncludeFiles(
    fixture):
  sched = fixture.conf.aSched().withTestOptions().write()

  fixture.conf.ruleWithSyncer("header.inc").withScheduler(sched).\
      withContent("""
[Scheduler]
Name = {sched}
Interval = 3w
[Synchronizer]
Name = {syncer}
""").write()

  fixture.conf.aRule("[actual]-rule").withContent("""
#import header
[Synchronizer]
Loc1={loc1}
Loc2={loc2}
[Scheduler]
Syslog = yes""").enabled().write()

  fixture.runSibt("show", "[actual]-rule")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldIncludeLinePatterns(
      "*[[]actual]-rule*",
      "*Interval = 3w*",
      "*Syslog = yes*",
      "*Loc1 =*")

  fixture.runSibt("show", "header.inc")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldIncludeInOrder("no", "rule", "name")
  fixture.stdout.shouldBeEmpty()

def test_shouldTreatInstanceFileAsImplicitOverridingImportFile(fixture):
  fixture.conf.aSyncer("rdiff-backup").withTestOptionsCode().write()
  fixture.conf.ruleWithSched("user-rule.inc").withContent(r"""
  _userName = dummy
  [Scheduler]
  Name = {sched}
  [Synchronizer]
  Loc1 = /home/%(_userName)s
  Loc2 = /mnt/backup/%(_userName)s""").write()

  fixture.conf.aRule("with-rdiff").withContent(r"""
  #import user-rule
  [Synchronizer]
  Name = rdiff-backup
  AddFlags = --exclude %(_excludePattern)s""").\
      enabled("user1", r"""
  _userName = %(_instanceName)s
  _excludePattern = *foo""").\
      enabled("user2", r"""
  _excludePattern = *bar
  [Synchronizer]
  Loc2 = /mnt/important/%(_userName)s
  _userName = blah""").write()


  fixture.runSibtWithRealStreamsAndExec("show", "user1@with-rdiff")
  fixture.stderr.shouldBeEmpty()
  fixture.stdout.shouldIncludeLinePatterns(
      "*Loc1 = /home/user1*",
      "*Loc2 = /mnt/backup/user1*",
      "*AddFlags = --exclude [*]foo*")

  fixture.runSibtWithRealStreamsAndExec("show", "user2@with-rdiff")
  fixture.stdout.shouldIncludeLinePatterns(
      "*Loc1 = /home/blah*",
      "*Loc2 = /mnt/important/blah*",
      "*AddFlags = --exclude [*]bar*")

def test_shouldProvideAWayInItsCliToWriteAndDeleteInstanceFiles(fixture):
  syncer = fixture.conf.aSyncer().withTestOptionsCode().write()
  fixture.conf.ruleWithSched("all-of-it!").withSynchronizer(syncer).write()

  fixture.runSibtWithRealStreamsAndExec("enable", "all-of-it!")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldInclude("enabled")
  fixture.runSibtWithRealStreamsAndExec("enable", "all-of-it!", 
      "[Synchronizer]", "KeepCopies = 5", "AddFlags = --blah", "--as=here")

  fixture.runSibtWithRealStreamsAndExec("show", "here@all-of-it!")
  fixture.stdout.shouldIncludeLinePatterns("*KeepCopies = 5*", "*AddFlags*")
  fixture.runSibtWithRealStreamsAndExec("list", "rules")
  fixture.stdout.shouldContainLinePatterns("*all-of-it!*enabled*",
      "*here@all-of-it!*")

  fixture.runSibtWithRealStreamsAndExec("disable", "here@all-of-it!")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldInclude("here")
  fixture.runSibtWithRealStreamsAndExec("list", "rules")
  fixture.stdout.shouldNotInclude("here")

  fixture.runSibtWithRealStreamsAndExec("disable", "here@all-of-it!")
  fixture.shouldHaveExitedWithStatus(1)

  fixture.runSibtWithRealStreamsAndExec("enable", "all-of-it!")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldIgnoreDisabledRulesThatNeedOptionsFromTheirInstanceFile(fixture):
  fixture.conf.ruleWithSchedAndSyncer("ignored-because-insufficient-options").\
      withLoc1("%(_instanceName)s").write()

  fixture.runSibt("list", "rules")
  fixture.stderr.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldBeEmpty()

def test_shouldMakeSchedulersCheckOptionsBeforeSchedulingAndAbortIfErrorsOccur(
    fixture):
  schedMock, errorSched = fixture.conf.aSched().\
      withName("uncontent-sched").mock()
  schedMock.check = lambda schedulings: ["this problem cannot be solved"] if \
      len(schedulings) == 2 else []

  _, permissiveSched = fixture.conf.aSched("content-sched").mock()

  enabledRule = fixture.conf.ruleWithSyncer().enabled()
  enabledRule.withName("badly-confd-rule").withScheduler(errorSched).write()
  enabledRule.withName("another-bad-rule").withScheduler(errorSched).write()
  enabledRule.withName("correctly-confd-rule").withScheduler(permissiveSched).\
      write()

  fixture.runSibt("schedule", "*")
  fixture.stderr.shouldInclude("badly-confd-rule", "another-bad-rule", 
      "uncontent-sched", "this problem cannot be solved")
  fixture.shouldHaveExitedWithStatus(1)

  errorSched.reRegister(schedMock)
  permissiveSched.mock()
  fixture.runSibt("schedule", "correctl*", "badly*")
  fixture.stderr.shouldNotInclude("correctly-confd")

def test_shouldFailAndPrintErrorIfExternalProgramReturnsErrorCode(fixture):
  syncer = fixture.conf.aSyncer("failing-syncer").withBashCode("""
      if [ $1 = available-options ]; then exit 4; else exit 200; fi""").write()
  fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  fixture.runSibtWithRealStreamsAndExec()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldInclude("failing-syncer", "error", "calling", "(4)",
      "arguments", "available-options")

def test_shouldPrintRuleNameIfSyncFailsAndAlsoNormalErrorMessageIfVerboseIsOn(
    fixture):
  failingSyncer = fixture.conf.aSyncer().withBashCode(
      "if [ $1 = sync ]; then exit 23; else exit 200; fi").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(failingSyncer).write()

  fixture.runSibtWithRealStreamsAndExec("sync-uncontrolled", rule.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("running", "rule", rule.name, "failed", "(23)")
  fixture.stderr.shouldNotInclude(str(failingSyncer.path))

  fixture.runSibtWithRealStreamsAndExec("--verbose", "sync-uncontrolled",
      rule.name)
  fixture.stderr.shouldInclude(str(failingSyncer.path))

  def failSyncing(args):
    if args[0] == "sync":
      raise FakeException()
  failingSyncer.allowing(execmock.call(failSyncing)).allowingSetupCalls().\
      reMakeExpectations()
  with pytest.raises(FakeException):
    fixture.runSibtCheckingExecs("sync-uncontrolled", rule.name)
  fixture.stderr.shouldInclude(rule.name, "failed", "unexpected error")

def test_shouldFailAndReportItIfAnSynchronizerDoesntSupportAFunction(fixture):
  syncer = fixture.conf.aSyncer("not-impld").withBashCode("exit 200").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  fixture.runSibtWithRealStreamsAndExec("sync-uncontrolled", rule.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldInclude("not-impld", "does not implement", "sync")

def test_shouldCollectVersionsOfAFileFromRulesThatHaveItWithinLoc1OrLoc2(
    fixture):
  fixture.confFolders.createSysFolders()
  fixture.setNormalUserId()

  utcThirdOfMarch = "2014-01-03T18:35:00"
  utcMarch3rdInDifferentZone = "2014-01-03T20:35:00+02:00"
  utc123 = "1970-01-01T00:02:03"

  testDir = fixture.tmpdir.mkdir("versions-test")
  dataDir = str(testDir) + "/home/foo/data"
  backupDir = str(testDir) + "/mnt/backup/data"
  fileName = "folder/some-file"
  fileInDataDir = os.path.join(dataDir, fileName)

  syncer = fixture.conf.syncerReturningVersions(
      forRelativeFile=fileName,
      ifWithinLoc1=[utcMarch3rdInDifferentZone, "0"],
      ifWithinLoc2=["123"]).asSysConfig().write()

  baseRule = fixture.conf.ruleWithSched().withSynchronizer(syncer)
  baseRule.withName("rule-1").\
      withLoc1(dataDir).\
      withLoc2(backupDir).asSysConfig().write()
  baseRule.withName("rule-2").\
      withLoc1(backupDir).\
      withLoc2(str(testDir) + "/mnt/remote").write()

  fixture.tmpdir.join("link").mksymlinkto(fileInDataDir)
  with fixture.tmpdir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of", "link/")
    fixture.stdout.shouldContainLinePatterns(
        "*rule-1," + utcThirdOfMarch + "*",
        "*rule-1," + Utc0 + "*")

  with testDir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of",
        "mnt/backup/data/" + fileName)
    fixture.stdout.shouldContainLinePatterns(
        "*rule-1," + utc123 + "*",
        "*rule-2," + utcThirdOfMarch + "*",
        "*rule-2," + Utc0 + "*")

  fixture.runSibtWithRealStreamsAndExec("versions-of", "/does-not-exist")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdout.shouldBeEmpty()

def test_shouldCorrectlyCallRestoreForTheVersionThatHasAllGivenSubstrings(
    fixture):
  def callRestore(*args):
    fixture.runSibtCheckingExecs("--utc", "restore", *args)

  dataDir = "/mnt/data/"
  backupDir = "/mnt/backup/"
  fileName = "file-to-restore"
  syncer = fixture.conf.aSyncer().allowingSetupCalls()
  baseRule = fixture.conf.ruleWithSched().withSynchronizer(syncer).\
      withLoc1(dataDir)
  baseRule.withName("total-backup").withLoc2(backupDir).write()
  baseRule.withName("other-rule").withLoc2("/mnt/quux").write()

  april5th = "2014-04-05T13:35:34+00:00"
  march3rd = "2014-03-30T21:43:12+00:00"
  april5thTimestamp = "1396704934"

  syncer = syncer.allowing(execmock.call(lambda args: args[0] == "versions-of",
    [april5th, march3rd])).write()

  callRestore(dataDir + fileName, "2014", "3:")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("patterns", "ambiguous")

  syncer.reMakeExpectations()
  callRestore(dataDir + fileName, "this-is-not-a-substring")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("patterns", "no match")

  syncer.expecting(execmock.call(lambda args: args[0] == "restore" and
    "Loc2=" + backupDir[:-1] in args and
    args[1:5] == (fileName, "1", april5thTimestamp,
      str(fixture.tmpdir) + "/dest.backup"))).reMakeExpectations()
  with fixture.tmpdir.as_cwd():
    callRestore(dataDir + fileName, "tota", "04", "--to=dest.backup")

def test_shouldGetANullSeparatedFileListingWithACallSimilarToRestore(fixture):
  syncer = fixture.conf.aSyncer().withBashCode(r"""
  if [ $1 = versions-of ]; then
    echo '1970-01-01T00:00:50+00:00'
    echo 100000000
  elif [[ $1 = list-files && $2 = container/folder && $3 = 2 && $4 = 50 ]]; then
    echo -n -e 'some\n-file'
    echo -n -e '\0'
    echo -n 'and-a-dir/'
    echo -n -e '\0'
  else exit 200; fi""").write()
  fixture.conf.ruleWithSched().withSynchronizer(syncer).\
      withLoc2("/var/spool").write()

  folder = "/var/spool/container/folder"
  fixture.runSibtWithRealStreamsAndExec("list-files",
    folder, "1970")
  fixture.stderr.shouldBeEmpty()
  fixture.stdout.shouldContainLinePatterns("some\\n-file",
      "and-a-dir/")

  fixture.runSibtWithRealStreamsAndExec("list-files", "--null", folder,
      "1970")
  fixture.stdout.shouldInclude("some\n-file\0", "and-a-dir/\0")

def test_shouldHaveAnOptionForARecursiveFileListing(fixture):
  syncer = fixture.conf.aSyncer().write()
  syncer = syncer.allowingSetupCalls().allowing(execmock.call(
    lambda args: args[0] == "versions-of", ret=["20"]))
  fixture.conf.ruleWithSched().withLoc1("/dir").withSynchronizer(syncer).write()

  syncer.expectingListFiles(lambda args: args[4] == "0").reMakeExpectations()
  fixture.runSibtCheckingExecs("list-files", "/dir/file", "1970")

  syncer.expectingListFiles(lambda args: args[4] == "1").reMakeExpectations()
  fixture.runSibtCheckingExecs("list-files", "-r", "/dir/file", "1970")

def test_shouldCallRunnerNamedInHashbangLineOfSynchronizersIfItExists(fixture):
  runnerPath = fixture.confFolders.writeRunner("faith")
  syncer = fixture.conf.aSyncer().withCode("#!faith").write()
  fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  anyCallsExceptOptions = execmock.call(
      lambda args: args[1] != "available-options",
      returningNotImplementedStatus=True)
  fixture.execs.allow(runnerPath, anyCallsExceptOptions)

  fixture.execs.expect(runnerPath, execmock.call(
      (str(syncer.path), "available-options")))
  fixture.runSibtCheckingExecs("list", "synchronizers")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldPerformSanityChecksBeforeSchedulingDependingOnRuleSettings(
    fixture):
  ruleWhoseLocsDontExist = fixture.conf.ruleWithNonExistentLocs("r-exist").\
      write()
  ruleWithEmptyLocs = fixture.conf.ruleWithSchedAndSyncer("r-empty").\
      withNewValidLocs(locsAreEmpty=True).write()
  ruleWhoseLocsDontExist.scheduler.withEmptyRunFuncCode().write()
  ruleWithEmptyLocs.scheduler.withEmptyRunFuncCode().write()

  fixture.runSibt("schedule", "r-exist")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldIncludeInOrder("r-exist", "not exist")
  fixture.runSibt("schedule", "r-empty")
  fixture.shouldHaveExitedWithStatus(0)

  ruleWhoseLocsDontExist.withOpts(LocCheckLevel="None").write()
  ruleWithEmptyLocs.withOpts(LocCheckLevel="None").write()
  fixture.runSibt("schedule", "r-exist", "r-empty")
  fixture.shouldHaveExitedWithStatus(0)

  ruleWhoseLocsDontExist.withOpts(LocCheckLevel="Strict").write()
  ruleWithEmptyLocs.withOpts(LocCheckLevel="Strict").write()
  fixture.runSibt("schedule", "r-exist")
  fixture.stderr.shouldInclude("not exist")
  fixture.runSibt("schedule", "r-empty")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldCheckIfTwoRulesToScheduleWouldWriteToTheSameLocation(fixture):
  bidirectional = fixture.conf.aSyncer().withBashCode("""
  if [ $1 = info-of-port ]; then
    if [ $2 != specials ] && [ $2 -lt 3 ]; then
      echo 1
      echo file
      echo ssh
    fi
  else exit 200; fi""").write()
  unidirectional = fixture.conf.aSyncer().withBashCode("""
    notImplementedCode=200
    exit $notImplementedCode
  """).write()

  fixture.conf.ruleWithSched("uni").withSynchronizer(unidirectional).\
      withNewValidLoc1("src/1").withNewValidLoc2("dest/1").write()
  fixture.conf.ruleWithSched("bi").withSynchronizer(bidirectional).\
      withNewValidLoc1("dest/1").withLoc2("ssh://somewhere/dest/2").write()

  fixture.runSibtWithRealStreamsAndExec("schedule", "uni", "bi")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("dest/1", "overlapping writes", "bi", "uni")

def test_shouldHaveACheckActionThatDoesTheSameChecksAsScheduleButDoesntSchedule(
    fixture):
  syncer1 = fixture.conf.aSyncer().allowingSetupCalls().write()
  fixture.conf.ruleWithSched("valid-rule").withSynchronizer(syncer1).write()

  fixture.runSibt("check", "valid-rule")
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(0)

  containerDir = fixture.confFolders.validSynchronizerLoc("container")
  subDir = fixture.confFolders.validSynchronizerLoc("container/sub-dir")

  unidirectional = fixture.conf.aSyncer().allowingSetupCallsExceptPorts().\
      writingToLoc2().write()
  fixture.conf.ruleWithSched("self-destruction").withSynchronizer(
      unidirectional).withLoc1(str(subDir)).withLoc2(str(containerDir)).write()
  syncer1.reMakeExpectations()

  fixture.runSibtCheckingExecs("check", "self-destruction", "valid-rule")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdout.shouldIncludeInOrder("destruction", "within", 
      str(containerDir)).andAlso.shouldNotInclude("valid-rule")

def test_shouldBeAbleToSimulateSchedulingsAndPrintThemToStdout(fixture):
  def fail(*args):
    assert False
  basicSched = fixture.conf.aSched().withRunFunc(fail)
  _, sched1 = basicSched.withName("sched-1").mock()
  _, sched2 = basicSched.withName("sched-2").mock()

  rule1 = fixture.conf.ruleWithSyncer("rule-1").withScheduler(sched1).write()
  rule2 = fixture.conf.ruleWithSyncer("rule-2").withScheduler(sched2).write()

  fixture.runSibt("schedule", "--dry", "rule-1", "rule-2")
  fixture.stdout.shouldContainLinePatterns(
      "scheduling*rule-1*sched-1*",
      "*rule-2*sched-2*")
  fixture.shouldHaveExitedWithStatus(0)

  rule1.withLoc1("/doesn't-exist").write()
  sched1.mock(); sched2.mock()
  fixture.runSibt("schedule", "--dry", "rule-1", "rule-2")
  fixture.stderr.shouldInclude("/doesn't-exist")
  fixture.stdout.shouldBeEmpty()

# TODO check slash removed
# remote loc test (with versions-of; change to ip later)
#def test_shouldSynchronizerAColonSeparatedFormatForRemoteLocations(fixture):
#  utc12 = "*1970-01-01T00:00:12*"
#
#  syncer = fixture.conf.syncerReturningVersions(forRelativeFile="raven",
#      ifWithinLoc1=["12"], ifWithinLoc2=[]).write()
##TODO scramble path
#  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).\
#      withLoc1("other-host:/mnt/data").write()
#  
#  fixture.runSibtWithRealStreamsAndExec("versions-of", 
#      "other-host:/mnt/data/raven")
#  fixture.stdout.shouldContainLinePatterns(utc12)

def test_shouldDissectRemoteLocationsWrittenAsUrlsForSyncers(fixture):
# TODO refactor to functionmodule; check allLocalRule 
#   (with file:/// and without; syntactic sugar test)
# TODO use ssh syntactic sugar somewhere else in a test
  rule = fixture.conf.ruleWithSched().\
      withLoc1("protocol1://bar@somehost/usr//share/").\
      withLoc2("http://foo:123/~/downloads").\
      withLoc3("/local-folder").\
      withLoc4("user@host-of-syntactic-sugar:foo")

  syncer = fixture.conf.aSyncer().expecting(execmock.call(
    lambda args: args[0] == "sync" and
      all(option in args for option in [
        "Loc1Protocol=protocol1",
        "Loc1Login=bar",
        "Loc1Host=somehost",
        "Loc1Port=",
        "Loc1Path=/usr/share",

        "Loc2Protocol=http",
        "Loc2Login=",
        "Loc2Host=foo",
        "Loc2Port=123",
        "Loc2Path=downloads",
        
        "Loc3Protocol=file",
        "Loc3Path=/local-folder",

        "Loc4Protocol=ssh",
        "Loc4Login=user",
        "Loc4Host=host-of-syntactic-sugar",
        "Loc4Port=",
        "Loc4Path=foo"]))).allowingSetupCallsExceptPorts().\
    allowing(execmock.call(lambda args: args[0] == "info-of-port" and
      args[1] in ["1", "2", "3", "4"], 
      ret=["0", "protocol1", "ssh", "http", "file"])).\
    allowing(execmock.call(lambda args: args[0] == "info-of-port" and
      args[1] in ["5", "specials"], ret=[])).write()

  rule = rule.withSynchronizer(syncer).write()

  fixture.runSibtCheckingExecs("sync-uncontrolled", rule.name)

def test_shouldComplainAboutUnsupportedRemoteProtocols(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCallsExceptPorts().\
      supportingProtocols([["foo", "bar", "file"],
        ["alternative", "blah", "file"]]).\
      allowing(execmock.call(lambda args: args == ("info-of-port", "specials"),
        ret=["one-must-be-file"])).write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer)

  rule.withLoc1("file:///folder/").withLoc2("bar://host/").write()

  fixture.runSibtCheckingExecs("show", rule.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldIncludeInOrder("Loc2", "can't", "bar", "choose",
      "alternative", "blah", "file").andAlso.shouldInclude(rule.name)

  syncer.reMakeExpectations()
  rule.withLoc1("foo://host/").withLoc2("blah://host/").write()
  fixture.runSibtCheckingExecs("show", rule.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude(rule.name, "one", "local path")

  syncer.reMakeExpectations()
  rule.withLoc1("file:///folder/").withLoc2("blah://host/").write()
  fixture.runSibtCheckingExecs("show", rule.name)
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldBeAbleToMakeContainsCheckForRemoteLocationsToo(fixture):
  syncer = fixture.conf.syncerReturningVersions("folder/file", ifWithinLoc1=
      ["48"], ifWithinLoc2=["0"]).allowingSetupCallsExceptPorts().write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).\
      withLoc1("/foo").withLoc2("ssh://foo@host/foo/").write()

  fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of",
      "foo@host:/foo/folder/file/")
  fixture.stdout.shouldContainLinePatterns("*" + rule.name + "," + Utc0 + "*")

  syncer.reMakeExpectations()

def test_shouldAllowRemoteLocationsForTheRestoreTarget(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCallsExceptPorts().\
      allowingPortSpecialsCalls(["one-must-be-file"]).\
      allowing(execmock.call(lambda args: args[0] == "versions-of" and \
          args[2] == "1", ret=["0"])).\
      supportingProtocols([
        ["first", "second", "file"],
        ["third", "fourth", "file"]]).write()

  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer)
  rule.withLoc1("/foo").withLoc2("third://h/").write()

  fixture.runSibtCheckingExecs("restore", "/foo/file", ":",
      "--to=first://h/the/dest")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("restore target", "one", "local")

  rule.withLoc1("/foo").withLoc2("/bar").write()

  syncer.reMakeExpectations()
  fixture.runSibtCheckingExecs("restore", "/foo/file", ":",
      "--to=fourth://h/the/dest")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("restore target", "can't have", "fourth")

  syncer.expecting(execmock.call(lambda args: args[0] == "restore" and
    "RestoreProtocol=first" in args and 
    "RestorePath=/the/dest" in args)).reMakeExpectations()
  fixture.runSibtCheckingExecs("restore", "/foo/file", ":",
      "--to=first://h/the/dest")

