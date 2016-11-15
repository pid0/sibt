import pytest
import os
import sys
from datetime import timedelta

from test.acceptance.sibtspec import SibtSpecFixture

from test.common.assertutil import strToTest
from test.common import mock
from test.common.builders import orderedDateTimes, constantTimeClock, \
    anyUTCDateTime

class SchedulerUsageSpecFixture(SibtSpecFixture):
  pass

@pytest.fixture
def fixture(tmpdir, capfd):
  return SchedulerUsageSpecFixture(tmpdir, capfd)

def test_shouldInitSchedulersCorrectlyIncludingSibtInvocationWithGlobalOpts(
    fixture):
  fixture.conf.aSched("prints-warnings").withInitFuncCode(
"""def init(args): args.logger.log(" ".join(args.sibtInvocation))""").write()

  newReadonlyDir = str(fixture.tmpdir)

  fixture.runSibtWithRealStreamsAndExec("--readonly-dir", newReadonlyDir,
      "list", "schedulers")
  fixture.stderr.shouldInclude("{0} --readonly-dir {1}".format(sys.argv[0],
      newReadonlyDir), "prints-warnings")

def test_shouldGiveEachSchedulerAnUnchangingVarDirectory(fixture):
  sched = fixture.conf.aSched("needs-lotsa-space")
  fixture.conf.ruleWithSyncer().withScheduler(sched).write()
  varDir = []
  def firstCall(args):
    assert os.path.basename(args.varDir) == "needs-lotsa-space"
    varDir.append(args.varDir)
    return True
  def secondCall(args):
    assert args.varDir == varDir[0]
    return True

  sched.mock()[0].expectCalls(mock.callMatching("init", firstCall))
  fixture.runSibt("list", "-f")
  sched.mock()[0].expectCalls(mock.callMatching("init", secondCall))
  fixture.runSibt("list", "-f")

def test_shouldMakeSchedulersCheckOptionsBeforeSchedulingAndAbortIfErrorsOccur(
    fixture):
  errorSchedMock, errorSched = fixture.conf.aSched().\
      withName("uncontent-sched").mock()
  errorSchedMock.check = lambda schedulings: ["this problem cannot be solved"] \
      if len(schedulings) == 2 else []

  permissiveSchedMock, permissiveSched = fixture.conf.aSched(
      "content-sched").mock()

  enabledRule = fixture.conf.ruleWithSyncer().enabled()
  enabledRule.withName("blows-with-2nd").withScheduler(errorSched).write()
  enabledRule.withName("blows-with-1st").withScheduler(errorSched).write()
  enabledRule.withName("rule-without-problems").withScheduler(permissiveSched).\
      write()

  fixture.runSibt("schedule", "*")
  fixture.stderr.shouldInclude("blows-with-2nd", "blows-with-1st", 
      "uncontent-sched", "this problem cannot be solved")
  fixture.shouldHaveExitedWithStatus(1)

  permissiveSchedMock.schedule = lambda *args: None
  errorSchedMock.schedule = lambda *args: None
  errorSched.reRegister(errorSchedMock)
  permissiveSched.reRegister(permissiveSchedMock)
  fixture.runSibt("schedule", "*-with-2nd", "*without*")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldNotScheduleIfAnyRuleDiffersFromTheOthersInASharedOption(fixture):
  schedMock, sched = fixture.conf.aSched().\
      withSharedOptions("f TmpFolder").mock()

  baseRule = fixture.conf.ruleWithSyncer().withScheduler(sched)
  rule1 = baseRule.withAnyName().withSchedOpts(TmpFolder="/tmp").write()
  rule2 = baseRule.withAnyName().withSchedOpts(TmpFolder="/tmp").write()

  schedMock.expectCalls(mock.callMatching("schedule", lambda schedulings:
    schedulings[0].options["TmpFolder"].path == "/tmp"))
  fixture.runSibt("schedule", rule1.name, rule2.name)
  fixture.stderr.shouldBeEmpty()
  fixture.shouldHaveExitedWithStatus(0)

  sched.mock()
  rule2.withSchedOpts(TmpFolder="/var/tmp").write()
  fixture.runSibt("schedule", rule1.name, rule2.name)
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("TmpFolder", "differ", "/tmp", "/var/tmp")

def test_shouldAllowSchedulersToControlRuleExecutions(fixture):
  def execute(execEnv, scheduling):
    execEnv.logger.log("something smart about {0}", scheduling.ruleName)
    succeeded = execEnv.runSynchronizer()
    return not succeeded
  
  fixture.replaceSibtSyncCallsWith(fixture.writeBashScript(r"""
  echo another thing
  exit 2"""))

  _, sched = fixture.conf.aSched().withExecuteFunc(execute).mock()
  rule = fixture.conf.ruleWithSyncer("a-rule").withScheduler(sched).write()

  fixture.runSibt("execute-rule", rule.name)

  execution = fixture.getSingleExecution(fixture.paths, None, rule.name)
  assert execution.succeeded is True
  strToTest(execution.output).shouldIncludeInOrder(
      "something smart about a-rule", "another thing")

def test_shouldProvideVariousOtherOptionsForControllingRuleExecutions(fixture):
  testFile = fixture.tmpdir / "testfile"
  script = "exit {exitCode}"

  rule = fixture.conf.ruleWithSchedAndSyncer("a-rule").withSchedOpts(
      Stderr="Yes",
      ExecOnFailure='echo an-error >&1; echo "$SIBT_RULE" >{0}'.format(
        testFile)).write()
  
  fixture.replaceSibtSyncCallsWith(fixture.writeBashScript(script.format(
    exitCode="0")))
  fixture.runSibtWithRealStreamsAndExec("execute-rule", rule.name)
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldBeEmpty()
  assert not os.path.isfile(str(testFile))

  fixture.replaceSibtSyncCallsWith(fixture.writeBashScript(script.format(
    exitCode="1")))
  fixture.runSibtWithRealStreamsAndExec("execute-rule", rule.name)
  assert testFile.read() == "a-rule\n"
  fixture.stderr.shouldInclude("an-error")

def test_shouldWarnWhenAccessingLocsIfTheNextRuleExecutionIsCloserThanAnHour(
    fixture):
  startTime, endTime, nextTime = orderedDateTimes(3)
  ruleName = "some-rule"
  nameAsSysRule = "+" + ruleName

  def nextExecutionTime(scheduling):
    assert scheduling.ruleName == nameAsSysRule
    assert scheduling.lastExecutionTime == endTime
    return nextTime

  syncer = fixture.conf.syncerHavingAnyVersions().asSysConfig().write()
  _, sched = fixture.conf.aSysSched().withNextExecutionTimeFunc(
      nextExecutionTime).mock()
  rule = fixture.conf.aSysRule(ruleName).withScheduler(sched).\
      withSynchronizer(syncer).allowedForTestUser().write()

  fixture.setRootUserId()
  fixture.executeOnce(rule, startTime, endTime)

  fixture.setNormalUserId()
  syncer.reMakeExpectations()
  fixture.setClock(constantTimeClock(nextTime - timedelta(minutes=59)))
  fixture.runSibtCheckingExecs("versions-of", str(rule.loc1))
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldContainLinePatterns("*:*")
  fixture.stderr.shouldInclude("warning", "execution", "less than 1", 
      nameAsSysRule)

  syncer.reMakeExpectations()
  fixture.runSibtCheckingExecs("versions-of", "/lala")
  fixture.stderr.shouldNotInclude("less than")

  syncer.expectingListFiles().reMakeExpectations()
  fixture.runSibtCheckingExecs("list-files", str(rule.loc1), ",")
  fixture.stderr.shouldInclude("warning", "less than")
  fixture.shouldHaveExitedWithStatus(0)

def test_shouldRequireForceOptionToRestoreWithARuleWhoseExecutionIsTooClose(
    fixture):
  now = anyUTCDateTime()
  fixture.setClock(constantTimeClock(now))

  _, sched = fixture.conf.aSched().withNextExecutionTimeFunc(
      lambda *_: now).mock()
  syncer = fixture.conf.syncerHavingAnyVersions().write()
  rule = fixture.conf.aRule().withScheduler(sched).withSynchronizer(syncer).\
      withLoc1("/mnt").write()

  fixture.runSibtCheckingExecs("restore", "/mnt", ":")
  fixture.shouldHaveExitedWithStatus(1)
  fixture.stderr.shouldInclude("error", "execution", "less than").but.\
      shouldNotInclude("warning", "matching")

  syncer.expectingRestore().reMakeExpectations()
  fixture.runSibtCheckingExecs("restore", "--force", "/mnt", ":")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stderr.shouldBeEmpty()
