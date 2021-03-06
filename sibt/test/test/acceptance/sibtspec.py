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

from sibt.infrastructure.coprocessrunner import CoprocessRunner
from sibt.infrastructure.fileobjoutput import FileObjOutput
from fnmatch import fnmatchcase
from test.acceptance.runresult import RunResult
from test.common.bufferingoutput import BufferingOutput
from test.common.execmock import ExecMock
from test.common import execmock
from py.path import local
from sibt import main
import pytest
import os
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
from test.common.builders import clockWithOrderedTimes, constantTimeClock, \
    anyUTCDateTime, toTimestamp
from test.common.rfc3164syslogserver import Rfc3164SyslogServer
from test.sibt.infrastructure.utillinuxsyslogger_test import loggerOptions
from datetime import timedelta, datetime, timezone
from test.common.presetcyclingclock import PresetCyclingClock
from contextlib import contextmanager
from test.common.fusefs import fuseIsAvailable, nonEmptyFSMountedAt

Utc0 = "1970-01-01T00:00:00"
TestPort = 5326

def decode(bytesObj):
  return bytesObj.decode(sys.getdefaultencoding(), errors="surrogateescape")

@contextmanager
def environmentVariables(**envVars):
  originalValues = dict(os.environ)
  try:
    os.environ.update(envVars)
    yield
  finally:
    os.environ.clear()
    os.environ.update(originalValues)

class SibtSpecFixture(object):
  def __init__(self, tmpdir, capfd):
    self.tmpdir = tmpdir
    userDir = tmpdir / "user"
    sysDir = tmpdir / "system"
    readonlyDir = tmpdir.mkdir("usr-share")

    self.paths = existingPaths(pathsIn(userDir, readonlyDir))
    self.sysPaths = existingPaths(pathsIn(sysDir, ""))
    self.fakePaths = pathsIn(tmpdir / "fakepaths", "")

    self.setNormalUserId()
    self.mockedSchedulers = dict()
    self.execs = ExecMock()
    self.capfd = capfd

    self.confFolders = ConfigFoldersWriter(self.sysPaths, self.paths, tmpdir)
    aScheduler = SchedulerBuilder(self.paths, self.sysPaths,
        self.confFolders, "sched", self.mockedSchedulers, dict())
    aSynchronizer = SynchronizerBuilder(self.paths, self.sysPaths,
        self.confFolders, "syncer", self.execs, dict())
    aRule = RuleBuilder(self.paths, self.sysPaths, self.confFolders,
        "rule", dict())
    self.conf = ConfigScenarioConstructor(self.confFolders, aSynchronizer,
        aScheduler, aRule)

    self.clock = constantTimeClock()
    self.disallowSibtSyncCalls()

    self.syslogOptions = loggerOptions(TestPort)
    self.userPathsAreRootUserPaths = False

  @property
  def stdout(self):
    return self.result.stdout
  @property
  def stderr(self):
    return self.result.stderr

  def writeBashScript(self, content):
    return self.writeScript("#!/usr/bin/env bash\n{0}".format(content))
  def writeScript(self, content):
    path = self.tmpdir / "script"
    path.write(content)
    path.chmod(0o700)
    return str(path)

  def getSingleExecution(self, paths, sysPaths, ruleName):
    from sibt.api import openLog
    log = openLog(sibtPaths=paths, sibtSysPaths=sysPaths)
    return log.executionsOfRules("*")[ruleName][0]

  def setClock(self, clock):
    self.clock = clock

  def replaceSibtSyncCallsWith(self, newCallToSync):
    self.callToSibtSync = lambda _: [newCallToSync]
  def allowSibtSyncCalls(self):
    self.replaceSibtSyncCallsWith("true")
  def disallowSibtSyncCalls(self):
    self.callToSibtSync = lambda _: ["/usr/bin/env", "bash", "-c",
        "echo called sibt sync>&2; exit 1"]

  def executeOnce(self, rule, startTime, endTime):
    self.setClock(PresetCyclingClock(startTime, endTime))
    self.allowSibtSyncCalls()
    self.runSibt("execute-rule", rule.name)
    self.shouldHaveExitedWithStatus(0)
    self.disallowSibtSyncCalls()

  def shouldHaveExitedWithStatus(self, expectedStatus):
    if self.result.exitStatus != expectedStatus and expectedStatus == 0:
      print(self.result.stderr.string)
    #print(self.result.exitStatus)
    assert self.result.exitStatus == expectedStatus

  def setNormalUserId(self):
    self.userId = 25
  def setRootUserId(self):
    self.userId = 0

  def getPathsForUser(self):
    if self.userId == 0 and not self.userPathsAreRootUserPaths:
      return self.sysPaths, self.fakePaths
    else:
      return self.paths, self.sysPaths

  def runSibtWithRealStreamsAndExec(self, *arguments):
    exitStatus = 1
    try:
      exitStatus = self._runSibt(FileObjOutput(sys.stdout.buffer),
          FileObjOutput(sys.stderr.buffer), CoprocessRunner(), arguments)
    except:
      self.result = RunResult(strToTest(""), strToTest(""), exitStatus)
      raise
    stdout, stderr = map(decode, self.capfd.readouterr())
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
    paths, sysPaths = self.getPathsForUser()
    exitStatus = main.run(arguments, stdout, stderr, processRunner,
      paths, sysPaths, "testUser", self.userId, moduleLoader, self.clock, 
      self.callToSibtSync)

    if len(self.mockedSchedulers) > 0:
      try:
        for mockedSched in self.mockedSchedulers.values():
          mockedSched.checkExpectedCalls()
      except:
        print(stderr.stringBuffer)
        raise

    return exitStatus

@pytest.fixture
def fixture(tmpdir, capfdbinary):
  return SibtSpecFixture(tmpdir, capfdbinary)

def test_shouldInvokeTheCorrectConfiguredSchedulersAndSynchronizers(fixture):
  sched = fixture.conf.aSched().withScheduleFuncCode("""
def schedule(args): print("scheduled rule '" + args[0].ruleName + "'")
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

  fixture.runSibtWithRealStreamsAndExec("sync", "foo-rule")
  fixture.stdout.shouldBe("one\n")

def test_shouldBeAbleToListOnlyRootUsersConfigurationOptionsToStdout(fixture):
  fixture.setRootUserId()
  fixture.userPathsAreRootUserPaths = True

  fixture.conf.writeAnyRule("rule-1", "sched-1", "syncer-1")
  fixture.conf.writeAnyRule("test-rule-2", "sched-2", "syncer-1")
  fixture.conf.writeAnyScheduler("sched-1")
  fixture.conf.writeAnyScheduler("sched-2")
  fixture.conf.writeAnySynchronizer("syncer-1")
  fixture.conf.writeAnySynchronizer("where-is-this?", sysConfig=True)

  fixture.runSibt("list", "synchronizers")
  fixture.stdout.shouldContainLinePatterns("*syncer-1*")

  fixture.runSibt("list", "schedulers")
  fixture.stdout.shouldContainLinePatterns("*sched-1*", 
      "*sched-2*")

  fixture.runSibt("list", "rules")
  fixture.stdout.shouldContainLinePatterns("*rule-1*", 
      "*test-rule-2*")

  fixture.runSibt("list", "all")
  fixture.stdout.shouldIncludeInOrder("synchronizers", "syncer-1")
  fixture.stdout.shouldInclude("rule-1", "test-rule-2", "sched-1", "sched-2")

def test_shouldAutomaticallyCreateFoldersIfTheyDontExist(fixture):
  fixture.confFolders.deleteConfigAndVarFolders()
  fixture.runSibt()

  for path in [fixture.paths.rulesDir, fixture.paths.schedulersDir,
      fixture.paths.synchronizersDir, fixture.paths.varDir]:
    assert os.path.isdir(path)

def test_shouldListAllowedSysConfigToANormalUserAsWellAsTheOwn(fixture):
  fixture.conf.writeAnyRule("normal-user-rule", "user-sched", "user-syncer")
  fixture.conf.writeAnyRule("system-rule", "system-sched", "system-syncer", 
      sysConfig=True, allowedForTestUser=True)
  fixture.conf.writeAnySynchronizer("user-syncer")
  fixture.conf.writeAnySynchronizer("system-syncer", sysConfig=True)
  fixture.conf.writeAnyScheduler("user-sched")
  fixture.conf.writeAnyScheduler("system-sched", sysConfig=True)

  fixture.runSibt("ls", "all")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldIncludeLinePatterns(
      "*normal-user-rule*",
      "*+system-rule*",
      "*user-syncer*",
      "*system-syncer*",
      "*user-sched*",
      "*system-sched*")

def test_shouldIgnoreSysRulesThatArentAllowedForTheCurrentUserOrUnreadable(
    fixture):
  syncer = fixture.conf.syncerReturningVersions(forRelativeFile="file",
      ifWithinLoc1=["500"]).write()

  baseRule = fixture.conf.ruleWithSched(isSysConfig=True).\
      withLoc1("/src").withLoc2("/dest").withSynchronizer(syncer)
  allowed = baseRule.withName("is-allowed").allowedForTestUser().write()
  allowedForNone = baseRule.withName("for-none").write()
  allowedForSomeoneElse = baseRule.withName("else").allowedFor("else").write()
  unreadable = baseRule.withName("unreadable").\
      enabledWithUnreadableFile("foo").write()

  fixture.runSibt("ls", "*")
  fixture.stdout.shouldContainLinePatterns("*is-allowed*")

  fixture.runSibt("ls", "+" + allowedForNone.name, 
      "+" + allowedForSomeoneElse.name)
  fixture.stdout.shouldContainLinePatterns("*", "*")

  fixture.runSibtWithRealStreamsAndExec("versions-of", "/src/file")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldContainLinePatterns("*is-allowed*")

  fixture.runSibt("ls", "+foo@unreadable")
  fixture.stderr.shouldInclude("permission")

  unreadableUserRule = fixture.conf.ruleWithSchedAndSyncer("user-rule").\
      enabledWithUnreadableFile("").write()
  fixture.runSibt("ls", "*")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldListDisallowedSysRulesAnywayIfShowSysIsOn(fixture):
  rule = fixture.conf.ruleWithSchedAndSyncer(isSysConfig=True).write()

  fixture.runSibt("ls", "--show-sys")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldInclude(rule.name)

def test_shouldExitWithErrorMessageIfInvalidSyntaxIsFound(fixture):
  fixture.conf.aRule("suspect-rule").withContent("sdafsdaf").write()
  fixture.conf.ruleWithSchedAndSyncer("some-valid-rule").write()

  fixture.runSibt("show", "suspect-rule", "some-valid-rule")
  fixture.stdout.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("wrong syntax", "suspect-rule").andAlso.\
      shouldNotInclude("some-valid")

  fixture.runSibt("list")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("wrong syntax")

def test_shouldIgnoreRulesThatAreNotNecessaryForTheCurrentOperation(fixture):
  fixture.conf.aRule("invalid").withContent("fubar").write()
  fixture.conf.ruleWithSchedAndSyncer("+invalid-name").write()
  fixture.conf.ruleWithSchedAndSyncer("valid").write()

  syncer = fixture.conf.aSyncer().allowingSetupCalls().expectingSync().write()
  fixture.conf.ruleWithSched("backup").withSynchronizer(syncer).write()

  fixture.runSibtCheckingExecs("sync", "backup")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldBeEmpty()

  fixture.runSibt("ls", "[!i]*id")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldInclude("valid")

def test_shouldDistinguishBetweenDisabledRulesAndEnabledOnesWithAnInstanceFile(
    fixture):
  rule = fixture.conf.ruleWithSchedAndSyncer("is-on").\
      enabled().\
      enabled(instanceName="foo").write()
  fixture.conf.ruleWithSchedAndSyncer("is-off").write()

  fixture.runSibt("list", "rules")
  fixture.stdout.shouldContainLinePatterns(
      "*is-on*[Ee]nabled*",
      "*foo@is-on*[Ee]nabled*",
      "*is-off*[Dd]isabled*")

def test_shouldFailIfConfiguredSchedulerOrSynchronizerDoesNotExist(fixture):
  fixture.conf.ruleWithSched("invalid-rule").\
      withSynchronizerName("is-not-there").write()
  fixture.conf.ruleWithSchedAndSyncer("valid-rule").write()

  fixture.runSibt()
  fixture.stdout.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("synchronizer", "is-not-there", "not found", 
      "run", "ls synchronizers")

def test_shouldPassParsedAndFormattedOptionsToSyncersAndSchedsBasedOnType(
    fixture):
  schedMock, sched = fixture.conf.aSched().\
      withOptions("High|Med|Low Verbosity", "t Interval").mock()
  syncer = fixture.conf.aSyncer().allowingSetupCallsExceptOptions().\
      withOptions("b Compress", "b Encrypt").write()

  rule = fixture.conf.aRule().\
      withSchedOpts(Verbosity="High", Interval="2m 5s").\
      withSyncerOpts(Compress=" on", Encrypt="nO").\
      withScheduler(sched).\
      withSynchronizer(syncer).write()

  schedMock.expectCallsInAnyOrder(mock.callMatching("schedule", 
    lambda schedulings: 
      len(schedulings) == 1 and
      schedulings[0].ruleName == rule.name and
      schedulings[0].options == dict(Verbosity="High", Interval=timedelta(
        minutes=2, seconds=5))))

  fixture.runSibtCheckingExecs("schedule", rule.name)

  syncer.expectingSync(lambda args: 
    "Loc1=" + rule.loc1 in args and
    "Compress=1" in args and
    "Encrypt=0" in args).reMakeExpectations()

  fixture.runSibtCheckingExecs("sync", rule.name)

def test_shouldFailIfOptionValuesHaveAnInvalidSyntax(fixture):
  sched = fixture.conf.aSched().withOptions("b StopAfterFailure").write()
  syncer = fixture.conf.aSyncer().allowingSetupCallsExceptOptions().\
      withOptions("p NoOfCopies").write()

  baseRule = fixture.conf.aRule().\
      withOpts(LocCheckLevel="None").\
      withSchedOpts(StopAfterFailure="Yes").\
      withSyncerOpts(NoOfCopies="3").\
      withScheduler(sched).\
      withSynchronizer(syncer).write()

  def run():
    syncer.reMakeExpectations()
    fixture.runSibtCheckingExecs("show", baseRule.name)
  fixture.execs.reset()

  run()
  fixture.shouldHaveExitedWithStatus(0)

  baseRule.withOpts(LocCheckLevel="dffd").write()
  run()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("pars", "opt", "LocCheckLevel", "dffd")

  baseRule.withSyncerOpts(NoOfCopies="-5").withSchedOpts(
      StopAfterFailure="hmm").write()
  run()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("NoOfCopies", "negative", "StopAfterFailure", 
      "hmm")

def test_shouldNicelyFormatOptionValuesBasedOnTypeSoTheyCouldBeParsed(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCallsExceptOptions().\
      withOptions("t DeleteAfter").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).\
      withOpts(LocCheckLevel="Strict").\
      withLoc1("file:///mnt").\
      withSyncerOpts(DeleteAfter="2w 1d 3 s").write()

  fixture.runSibtCheckingExecs("show", rule.name)
  fixture.stdout.shouldIncludeLinePatterns(
      "*LocCheck*Strict*",
      "*Loc1*/mnt*",
      "*DeleteAfter*=?2 weeks 1 day 3 seconds*")

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

def test_shouldIssueErrorMessageIfARuleFileNameContainsAComma(fixture):
  fixture.conf.ruleWithSchedAndSyncer("comma,2015-01-01").enabled(
      instanceName="no,").write()

  fixture.runSibt()
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldInclude("invalid character", "no,@comma")
def test_shouldIssueErrorMessageIfARuleFileNameContainsASpace(fixture):
  fixture.conf.ruleWithSchedAndSyncer("no space-in-crontab").write()

  fixture.runSibt()
  fixture.stderr.shouldInclude("invalid character", "no space-in")
def test_shouldIssueErrorMessageIfARuleFileNameBeginsWithAPlus(fixture):
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

def test_shouldScheduleEnabledRulesIfMatchedByPatternsAndDisabledOnesIfExactly(
    fixture):
  schedMock, sched = fixture.conf.aSched().mock()

  disabledRule = fixture.conf.ruleWithSyncer().withScheduler(sched)
  enabledRule = disabledRule.enabled()

  for name in ["rule-a1", "rule-a2", "rule-b", "exact[-]match"]:
    enabledRule.withName(name).write()
  for name in ["disabled-1", "disabled-2"]:
    disabledRule.withName(name).write()

  schedMock.expectCallsInAnyOrder(mock.callMatching("schedule", 
    lambda schedulings: iterableContainsPropertiesInAnyOrder(schedulings,
      lambda scheduling: scheduling.ruleName,
      equalsPred("rule-a1"), equalsPred("rule-a2"),
      equalsPred("disabled-2"), equalsPred("exact[-]match"))))

  fixture.runSibt("schedule", "*a[0-9]", "disabled-2", "exact[-]match")

def test_shouldExitWithErrorMessageIfNoRuleNamePatternMatches(fixture):
  fixture.conf.ruleWithSchedAndSyncer("valid-rule").write()

  fixture.runSibt("schedule", "valid-rule", "foo")
  fixture.stderr.shouldInclude("no rule matching", "foo")
  fixture.stderr.shouldNotInclude("valid-rule")
  fixture.shouldHaveExitedWithStatus(1)

def test_shouldScheduleRulesMatchedByMultiplePatternsOnlyOnce(fixture):
  schedMock, sched = fixture.conf.aSched().mock()

  baseRule = fixture.conf.ruleWithSyncer().withScheduler(sched).enabled()
  for name in ["a1", "a2", "b1", "b2", "c1", "c2"]:
    baseRule.withName(name).write()

  schedMock.expectCallsInAnyOrder(mock.callMatching("schedule", 
    lambda schedulings: len([scheduling for scheduling in schedulings if 
      scheduling.ruleName == "a1"]) == 1))

  fixture.runSibt("schedule", "?1", "a?", "a1")

def test_shouldRequireAnExactRuleNameMatchWhenSyncing(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCalls()
  rule = fixture.conf.ruleWithSched("[rule]a*b").withSynchronizer(syncer).\
    enabled().write()

  syncer.expecting(execmock.call(lambda args: args[0] == "sync")).write()
  fixture.runSibtCheckingExecs("sync", rule.name)

  syncer.reMakeExpectations()
  fixture.runSibtCheckingExecs("sync", "*")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("no rule")

def test_shouldDistinguishSysRulesFromNormalRulesByPuttingAPlusInFront(fixture):
  fixture.conf.ruleWithSchedAndSyncer("system-wide", isSysConfig=True).\
      withLoc1("/boot/grub").write()

  fixture.runSibt("show", "+system-wide")
  fixture.stdout.shouldInclude("/boot/grub", "+system-wide")

def test_shouldIgnoreSysRulesWhenSchedulingAndSyncing(fixture):
  fixture.conf.ruleWithSchedAndSyncer("otherwise-allowed", isSysConfig=True).\
      allowedForTestUser().write()

  fixture.runSibt("schedule", "*+otherwise-allowed")
  fixture.stderr.shouldInclude("no rule", "otherwise")

  fixture.runSibt("sync", "+otherwise-allowed")
  fixture.stderr.shouldInclude("no rule", "otherwise")

def test_shouldSupportCommandLineOptionToCompletelyIgnoreSysConfig(fixture):
  fixture.conf.aSched("own-sched").write()
  sched = fixture.conf.aSysSched().withName("systemd").write()
  syncer = fixture.conf.aSysSyncer().withName("tar").write()
  fixture.conf.aSysRule().withName("os-backup").allowedForTestUser().\
      withScheduler(sched).withSynchronizer(syncer).write()

  fixture.runSibt("--no-sys-config", "list", "all")
  fixture.stdout.shouldInclude("own-sched")
  fixture.stdout.shouldNotInclude("systemd", "tar", "os-backup")

def test_shouldAdditionallyReadSynchronizersAndSchedulersFromReadonlyDir(
    fixture):
  fixture.confFolders.createReadonlyFolders()

  fixture.conf.aSched("included-scheduler").write(toReadonlyDir=True)
  fixture.conf.aSyncer("included-synchronizer").write(
      toReadonlyDir=True)

  fixture.runSibt("list", "all")
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
  fixture.confFolders.createReadonlyFolders()
  sched = fixture.conf.aSched().withTestOptions().write()

  fixture.conf.ruleWithSyncer("header.inc").withScheduler(sched).\
      withContent("""
[Scheduler]
Name = {sched}
Interval = 3w
[Synchronizer]
Name = {syncer}
""").write(toReadonlyDir=True)

  fixture.conf.aRule("[actual]-rule").withContent("""
#import header
[Synchronizer]
Loc1={loc1}
Loc2={loc2}
[Scheduler]
StopAfterFailure = yes""").enabled().write()

  fixture.runSibt("show", "[actual]-rule")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldIncludeLinePatterns(
      "*[[]actual]-rule*",
      "*Interval = 3w*",
      "*StopAfterFailure = yes*",
      "*Loc1 =*")

  fixture.runSibt("show", "header.inc")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldIncludeInOrder("no", "rule", "header.inc")
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
  fixture.stdout.shouldContainLinePatterns("*all-of-it!*Enabled*",
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

def test_shouldIgnoreOptionInterpolationErrorsWhenMatchingMultipleDisabledRules(
    fixture):
  syncer = fixture.conf.syncerHavingAnyVersions().write()
  fixture.conf.ruleWithSched("valid").withLoc2("/tmp").\
      withSynchronizer(syncer).write()
  fixture.conf.ruleWithSched("not-enough-options").withSynchronizer(syncer).\
      withLoc1("%(_instanceName)s").withLoc2("/tmp").write()

  fixture.runSibt("list", "rules")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldBeEmpty()
  fixture.stdout.shouldContainLinePatterns("*valid*", 
      "*not-enough*[Dd]isabled*")

  fixture.runSibt("ls", "rules", "*")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldInclude("not-enough")

  fixture.runSibt("list", "rules", "-f")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.ignoringFirstLine.shouldContainLinePatterns("*valid*")

  syncer.reMakeExpectations()
  fixture.runSibtCheckingExecs("versions-of", "/tmp/foo")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldContainLinePatterns("*valid*")

  syncer.reMakeExpectations()
  fixture.runSibtCheckingExecs("schedule", "not-enough-options")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("instanceName")

def test_shouldAlwaysTreatEnabledRulesWithMissingOptionsAsErrors(fixture):
  fixture.conf.ruleWithSchedAndSyncer().enabled().\
      withLoc1("%(_missingOption)s").write()

  fixture.runSibt("schedule", "*")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("missingOption")

def test_shouldOnlyScheduleIfEachRulePassesACheckOfItsSynchronizer(fixture):
  syncer = fixture.conf.aSyncer("finds-errors").withBashCode(r"""
    if [ "$1" = available-options ]; then
      echo Id
    elif [ "$1" = check ]; then
      case "$*" in
        *Id=first*) 
          echo -n foo; echo -n -e '\0';;
        *Id=second*) 
          echo -n bar; echo -n -e '\0'
          echo -n $'baz\n  quux'; echo -n -e '\0';;
        *Id=third*)
          echo third-checked >&2;;
      esac
    else
      exit 200
    fi""").write()

  enabledRule = fixture.conf.ruleWithSched().withSynchronizer(syncer).enabled()
  enabledRule.withName("first").withSyncerOpts(Id="first").write()
  enabledRule.withName("second").withSyncerOpts(Id="second").write()
  enabledRule.withName("third").withSyncerOpts(Id="third").write()

  fixture.runSibtWithRealStreamsAndExec("schedule", "*")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("finds-errors", "synchronizer").andAlso.\
      shouldInclude("first", "second", "foo", "bar\n", "baz\n", "quux").but.\
      shouldNotInclude("\0")

  fixture.runSibtWithRealStreamsAndExec("check", "third")
  fixture.stderr.shouldInclude("third-checked")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldFailAndPrintErrorIfExternalProgramReturnsErrorCode(fixture):
  syncer = fixture.conf.aSyncer("failing-syncer").withBashCode("""
      if [ $1 = available-options ]; then exit 4; else exit 200; fi""").write()
  fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  fixture.runSibtWithRealStreamsAndExec()
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldInclude("failing-syncer", "error when calling", "(4)",
      "arguments", "available-options")

def test_shouldPrintRuleNameIfSyncFailsAndAlsoNormalErrorMessageIfVerboseIsOn(
    fixture):
  failingSyncer = fixture.conf.aSyncer().withBashCode(
      "if [ $1 = sync ]; then exit 23; else exit 200; fi").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(failingSyncer).write()

  fixture.runSibtWithRealStreamsAndExec("sync", rule.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("running", "rule", rule.name, "failed", "(23)")
  fixture.stderr.shouldNotInclude(str(failingSyncer.path))

  fixture.runSibtWithRealStreamsAndExec("--verbose", "sync", rule.name)
  fixture.stderr.shouldInclude(str(failingSyncer.path))

  def failSyncing(args):
    if args[0] == "sync":
      raise FakeException()
  failingSyncer.allowing(execmock.call(failSyncing)).allowingSetupCalls().\
      reMakeExpectations()
  with pytest.raises(FakeException):
    fixture.runSibtCheckingExecs("sync", rule.name)
  fixture.stderr.shouldInclude(rule.name, "failed", "unexpected error")

def test_shouldFailAndReportItIfASynchronizerDoesntSupportAFunction(fixture):
  syncer = fixture.conf.aSyncer("not-impld").withBashCode("exit 200").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  fixture.runSibtWithRealStreamsAndExec("sync", rule.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stdout.shouldBeEmpty()
  fixture.stderr.shouldInclude("not-impld", "does not implement", "sync")

def test_shouldCollectVersionsOfAFileFromRulesThatHaveItWithinLoc1OrLoc2(
    fixture):
  utcThirdOfMarch = "2014-01-03T18:35:00" 
  utc123 = "1970-01-01T00:02:03"

  testDir = fixture.tmpdir.mkdir("versions-test")
  dataDir = str(testDir) + "/home/foo/data"
  backupDir = str(testDir) + "/mnt/backup/data"
  fileName = "folder/some-file"
  fileInDataDir = os.path.join(dataDir, fileName)

  syncer = fixture.conf.syncerReturningVersions(
      forRelativeFile=fileName,
      ifWithinLoc1=[toTimestamp(utcThirdOfMarch), "0"],
      ifWithinLoc2=["123"]).asSysConfig().write()

  baseRule = fixture.conf.ruleWithSched().withSynchronizer(syncer)
  baseRule.withName("rule-1").\
      withLoc1(dataDir).\
      withLoc2(backupDir).asSysConfig().allowedForTestUser().write()
  baseRule.withName("rule-2").\
      withLoc1(backupDir).\
      withLoc2(str(testDir) + "/mnt/remote").write()

  fixture.tmpdir.join("link").mksymlinkto(fileInDataDir)
  with fixture.tmpdir.as_cwd():
    fixture.runSibtWithRealStreamsAndExec("--utc", "versions-of", "link/")
    fixture.stderr.shouldBeEmpty()
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

  april5th = "2014-04-05T13:35:34"
  march3rd = "2014-03-30T21:43:12"

  syncer = syncer.allowing(execmock.call(lambda args: args[0] == "versions-of",
    [toTimestamp(april5th), toTimestamp(march3rd)])).write()

  callRestore(dataDir + fileName, "2014", "3:")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("patterns", "ambiguous")

  syncer.reMakeExpectations()
  callRestore(dataDir + fileName, "this-is-not-a-substring")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("no matching")

  syncer.expecting(execmock.call(lambda args: args[0] == "restore" and
    "Loc2=" + backupDir[:-1] in args and
    args[1:5] == (fileName, "1", toTimestamp(april5th) + ",0",
      str(fixture.tmpdir) + "/dest.backup"))).reMakeExpectations()
  with fixture.tmpdir.as_cwd():
    callRestore(dataDir + fileName, "tota", "04", "--to=dest.backup")

def test_shouldGetANullSeparatedFileListingWithACallSimilarToRestore(fixture):
  syncer = fixture.conf.aSyncer().withBashCode(r"""
  if [ $1 = versions-of ]; then
    echo 50,325
    echo 100000000
  elif [[ $1 = list-files && $2 = container/folder && $3 = 2 && \
      $4 = 50,325 ]]; then
    echo -n -e 'some\xfc\n-file'
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
  fixture.stdout.shouldContainLinePatterns(
      "some" + decode(b"\xfc") + "\\n-file",
      "and-a-dir/")

  fixture.runSibtWithRealStreamsAndExec("list-files", "--null", folder,
      "1970")
  fixture.stdout.shouldInclude(
      "some" + decode(b"\xfc") + "\n-file\0",
      "and-a-dir/\0")

def test_shouldHaveAnOptionForARecursiveFileListing(fixture):
  syncer = fixture.conf.syncerHavingAnyVersions().write()
  fixture.conf.ruleWithSched().withLoc1("/dir").withSynchronizer(syncer).write()

  syncer.expectingListFiles(lambda args: args[4] == "0").reMakeExpectations()
  fixture.runSibtCheckingExecs("list-files", "/dir/file", "1970")

  syncer.expectingListFiles(lambda args: args[4] == "1").reMakeExpectations()
  fixture.runSibtCheckingExecs("list-files", "-r", "/dir/file", "1970")

def test_shouldCallRunnerNamedInHashbangLineOfSynchronizersIfItExists(fixture):
  runnerPath = fixture.confFolders.writeRunner("faith")
  syncer = fixture.conf.aSyncer().withCode("#!faith").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  anyCallsExceptSync = execmock.call(
      lambda args: args[1] != "sync",
      returningNotImplementedStatus=True, delimiter=execmock.DontCheck)
  fixture.execs.allow(runnerPath, anyCallsExceptSync)

  fixture.execs.expect(runnerPath, execmock.call(
    lambda args: args[0] == syncer.path and args[1] == "sync"))
  fixture.runSibtCheckingExecs("sync", rule.name)
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldPerformSanityChecksBeforeSchedulingDependingOnRuleSettings(
    fixture):
  ruleWhoseLocsDontExist = fixture.conf.ruleWithNonExistentLocs("r-exist").\
      write()
  ruleWithEmptyLocs = fixture.conf.ruleWithSchedAndSyncer("r-empty").\
      withNewValidLocs(locsAreEmpty=True).write()
  ruleWhoseLocsDontExist.scheduler.withEmptyScheduleFuncCode().write()
  ruleWithEmptyLocs.scheduler.withEmptyScheduleFuncCode().write()

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

  ruleWhoseLocsDontExist2 = fixture.conf.ruleWithNonExistentLocs("r-exist2").\
      write()
  fixture.runSibt("schedule", "r-exist", "r-exist2")
  fixture.stderr.shouldInclude(ruleWhoseLocsDontExist.loc1,
      ruleWhoseLocsDontExist.loc2, ruleWhoseLocsDontExist2.loc1)

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
  basicSched = fixture.conf.aSched().withScheduleFunc(fail)
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

def test_shouldDissectRemoteLocationsWrittenAsUrlsForSyncers(fixture):
  rule = fixture.conf.ruleWithSched().withOpts(LocCheckLevel="None").\
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

  fixture.runSibtCheckingExecs("sync", rule.name)

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

def test_shouldPrintHelpMessageIfInvalidCliArgsAreGiven(fixture):
  fixture.runSibt("--huh?")
  fixture.shouldHaveExitedWithStatus(2)
  fixture.stderr.shouldInclude("unknown", "--huh?",
      "Usage", "[--config-dir").andAlso.shouldNotInclude("sync")

  fixture.runSibt("list", "rules", "--help")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldNotInclude("unknown").andAlso.\
      shouldInclude("Usage", "[--full]")

def test_shouldProvideAccessToExecutionStatisticsViaAPythonInterface(fixture):
  fixture.setClock(clockWithOrderedTimes(4))
  firstTime, secondTime, thirdTime, fourthTime = fixture.clock.dateTimes

  rule = fixture.conf.ruleWithSchedAndSyncer("rule").write()

  script = """#!/usr/bin/env bash
  if [ "$1" != {0} ]; then
    exit
  fi
  echo {{0}}
  echo on stderr >&2
  exit {{1}}""".format(rule.name)

  fixture.replaceSibtSyncCallsWith(fixture.writeScript(script.format(
    "normal", "0")))
  fixture.runSibtWithRealStreamsAndExec("execute-rule", rule.name)

  fixture.replaceSibtSyncCallsWith(fixture.writeScript(script.format(
    "second", "1")))
  fixture.runSibtWithRealStreamsAndExec("execute-rule", rule.name)
  fixture.shouldHaveExitedWithStatus(3)
  fixture.stderr.shouldBeEmpty()

  from sibt.api import openLog

  log = openLog(sibtPaths=fixture.paths, sibtSysPaths=None)
  iterToTest(log.executionsOfRules("*")[rule.name]).shouldContainMatching(
      lambda execution: 
        execution.output == "normal\non stderr\n" and
        execution.startTime == firstTime and
        execution.endTime == secondTime and
        execution.succeeded == True,
      lambda execution: 
        execution.output == "second\non stderr\n" and
        execution.startTime == thirdTime and
        execution.endTime == fourthTime and
        execution.succeeded == False)

def test_shouldReadSysAlongsideUserStatistics(fixture):
  time = anyUTCDateTime()
  fixture.setClock(constantTimeClock(time))

  fixture.setRootUserId()

  fixture.conf.ruleWithSchedAndSyncer("shocked", isSysConfig=True).write()

  fixture.allowSibtSyncCalls()
  fixture.runSibtWithRealStreamsAndExec("execute-rule", "shocked")

  fixture.setNormalUserId()
  from sibt.api import openLog
  assert openLog(sibtPaths=fixture.paths, sibtSysPaths=fixture.sysPaths).\
      executionsOfRules("*")["+shocked"][0].endTime == time

def test_shouldAllowLoggingOutputOfExecutionsToOtherPlacesAsWell(fixture):
  script = fixture.writeBashScript(r"""
  echo foo
  echo bar >&2
  """)
  fixture.replaceSibtSyncCallsWith(script)

  logFile = fixture.tmpdir / "logfile"

  rule = fixture.conf.ruleWithSchedAndSyncer("them-all").withSchedOpts(
      LogFile=str(logFile),
      Stderr="Yes",
      Syslog="True",
      SyslogOptions=fixture.syslogOptions).write()

  with Rfc3164SyslogServer(TestPort) as syslogServer:
    fixture.runSibtWithRealStreamsAndExec("execute-rule", rule.name)
  fixture.shouldHaveExitedWithStatus(0)

  fixture.stderr.shouldBe("foo\nbar\n")

  strToTest(logFile.read()).shouldIncludeLinePatterns(
      "*them-all*foo", "*them-all*bar")

  iterToTest(syslogServer.packets).shouldContainMatching(
      lambda packet: b"them-all: foo" in packet.message,
      lambda packet: b"them-all: bar" in packet.message and
        packet.facility == "user" and
        packet.severity == "info" and
        packet.tag == b"sibt")

  from sibt.api import openLog
  log = openLog(sibtPaths=fixture.paths, sibtSysPaths=None)
  assert log.executionsOfRules("*")[rule.name][0].output == "foo\nbar\n"

def test_shouldAutomaticallyLogOntoStderrIfVerboseIsOneWhenExecuting(fixture):
  rule = fixture.conf.ruleWithSchedAndSyncer().write()

  fixture.replaceSibtSyncCallsWith(fixture.writeBashScript(
    "echo singularly-dreary"))

  fixture.runSibtWithRealStreamsAndExec("execute-rule", "-v", rule.name)
  fixture.stderr.shouldContainLinePatterns("singularly-dreary")

def test_shouldLogInternalExceptionsToo(fixture):
  logFile = fixture.tmpdir / "logfile"
  logFile.write("")
  logFile.chmod(0o400)

  rule = fixture.conf.ruleWithSchedAndSyncer().withSchedOpts(
      LogFile=str(logFile)).write()

  with pytest.raises(PermissionError):
    fixture.runSibt("execute-rule", rule.name)

  strToTest(fixture.getSingleExecution(fixture.paths, None, rule.name).output).\
      shouldInclude("permission denied")

def test_shouldPerformTheSameScheduleSanityChecksWhenSyncing(fixture):
  syncer = fixture.conf.aSyncer().allowingSetupCalls().write()
  rule = fixture.conf.ruleWithNonExistentLocs("my-locs-are-gone").\
      withSynchronizer(syncer).write()

  fixture.runSibtCheckingExecs("sync", "my-locs-are-gone")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("my-locs-are-gone", "not exist",
      "running", "failed")

def test_shouldPrintSeveralAdvancedRuleAttributesInANeatTable(fixture):
  sched = fixture.conf.aSched().write()
  rule = fixture.conf.ruleWithSyncer("sys-backup").withScheduler(sched).write()
  rule2 = rule.withName("sｅcond").write()

  startTime, endTime = \
      datetime(1976, 5, 20, 15, 0, 0, 0, timezone.utc), \
      datetime(1976, 5, 20, 18, 0, 0, 0, timezone.utc)
  fixture.executeOnce(rule, startTime, endTime)

  now = anyUTCDateTime()
  fixture.setClock(constantTimeClock(now))
  sched.withNextExecutionTimeFunc(lambda *_: now + timedelta(minutes=8)).mock()

  fixture.runSibt("--utc", "ls", "-f", "*")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldContainLinePatterns(
      "*Name*Last [Ee]xecution*Last [Ss]tatus*Next*",
      "*sys-backup*1976*Succeeded*In 8m*",
      "*sｅcond*n/a*In 8m*")

  fixture.stdout.ignoringFirstLine.shouldBeginInTheSameColumn("In 8m")

def test_shouldSortRulesWhenListing(fixture):
  baseRule = fixture.conf.ruleWithSchedAndSyncer()
  baseRule.withName("arule").write()
  baseRule.withName("brule").write()
  fixture.runSibt("list", "-f")
  fixture.stdout.ignoringFirstLine.shouldContainLinePatternsInOrder(
      "*arule*",
      "*brule*")

def test_shouldUseColorsAndWrapLinesWhenPrintingToTTY(fixture):
  fixture.conf.ruleWithSchedAndSyncer("very-long-backup-rule-name").write()

  with environmentVariables(COLUMNS="25"):
    fixture.runSibt("--tty", "list", "-f")
  fixture.shouldHaveExitedWithStatus(0)

  fixture.stdout.shouldInclude("\033[0m")

  plainStdout = fixture.stdout.ignoringEscapeSequences
  plainStdout.shouldHaveLinesNoWiderThan(25)
  nameCol = plainStdout.splitColumns()[0]
  assert len(nameCol.lines()) > 2
  nameCol.onlyAlphanumeric().shouldBe("Namevery-long-backup-rule-name")

def test_shouldIncludeTheAssertionThatALocMustBeAMountPointAmongItsSanityChecks(
    fixture):
  if not fuseIsAvailable():
    pytest.skip("FUSE is required")

  ruleName = "from-mount-point-to-mount-point"
  rule = fixture.conf.ruleWithSchedAndSyncer(ruleName).withOpts(
      MustBeMountPoint="1, 2").write()

  with nonEmptyFSMountedAt(rule.loc1):
    assert os.listdir(rule.loc1) == ["fuse-file"]
    with nonEmptyFSMountedAt(rule.loc2):
      fixture.runSibt("check", ruleName)
      fixture.shouldHaveExitedWithStatus(0)

    fixture.runSibt("check", ruleName)
    fixture.shouldHaveExitedWithStatus(1)
    fixture.stdout.shouldInclude(ruleName, "Loc2", "mount point").but.\
        shouldNotInclude("Loc1")

  with nonEmptyFSMountedAt(rule.loc2):
    fixture.runSibt("check", ruleName)
    fixture.stdout.shouldInclude(ruleName, "Loc1", "mount point").but.\
        shouldNotInclude("Loc2")

def test_shouldNeverTextDecodeAnyFileNames(fixture):
  dataDir = b"/mnt/f\xfcr Daten".decode(errors="surrogateescape")
  syncer = fixture.conf.aSyncer().allowingSetupCalls().allowing(
      execmock.call(lambda args: args[0] == "versions-of" and
        ("Loc1Path={}".format(dataDir)) in args, ["0"])).write()
  fixture.conf.ruleWithSched().withSynchronizer(syncer).withLoc1(dataDir).\
      write()

  fixture.runSibtCheckingExecs("--utc", "versions-of", dataDir +
      b"/file \xfc".decode(errors="surrogateescape"))
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldInclude("1970")

def test_shouldOnlyShowAnInfoMessageWhenTheVersionOptionIsPassed(fixture):
  fixture.runSibt("--version", "versions-of", "foo")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldInclude("version")
  fixture.stdout.shouldInclude("Copyright")
