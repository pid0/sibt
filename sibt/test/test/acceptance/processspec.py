import pytest
from test.acceptance.sibtspec import SibtSpecFixture
from py import path
from test.common import relativeToProjectRoot
from test.common.assertutil import strToTest
import shutil
import os
import threading
from test.acceptance.runresult import RunResult
import io
from test.common.assertutil import strToTest
import sys
import time
import signal
import io
import fcntl
import select
from test.acceptance.sighandler import SigHandler

def fillPipe(writeFd):
  flags = fcntl.fcntl(writeFd, fcntl.F_GETFL)
  fcntl.fcntl(writeFd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
  chunk = b"a"

  while True:
    try:
      os.write(writeFd, chunk)
    except io.BlockingIOError:
      if select.select([], [writeFd], [], 0.1) == ([], [], []):
        break
      continue

  fcntl.fcntl(writeFd, fcntl.F_SETFL, flags)

class ForkExecSubProcess(object):
  def __init__(self, args, blockingStdout, stdoutReadFdClosed):
    stdoutRead, stdoutWrite = os.pipe()
    stderrRead, stderrWrite = os.pipe()
    if hasattr(os, "set_inheritable"):
      for fd in [stdoutWrite, stderrWrite]:
        os.set_inheritable(fd, True)

    if blockingStdout:
      fillPipe(stdoutWrite)

    pid = os.fork()
    if pid == 0:
      os.setpgid(0, 0)
      os.close(stdoutRead)
      os.close(stderrRead)
      os.dup2(stdoutWrite, 1)
      os.dup2(stderrWrite, 2)
      os.close(stdoutWrite)
      os.close(stderrWrite)
      os.execv(args[0], args)
    else:
      try:
        os.setpgid(pid, 0)
      except OSError:
        pass
      os.close(stdoutWrite)
      os.close(stderrWrite)
      if not blockingStdout:
        self.stdout = os.fdopen(stdoutRead, "br")
      if stdoutReadFdClosed:
        self.stdout.close()
      self.stderr = os.fdopen(stderrRead, "br")
      self.pid = pid

  def wait(self):
    pid, exitStatus = os.waitpid(self.pid, 0)
    if os.WIFSIGNALED(exitStatus):
      self.returncode = -os.WTERMSIG(exitStatus)
    elif os.WIFEXITED(exitStatus):
      self.returncode = os.WEXITSTATUS(exitStatus)
    return self.returncode

  def sigKill(self):
    os.kill(self.pid, signal.SIGKILL)

  def __enter__(self):
    return self

  def __exit__(self, x, y, z):
    if hasattr(self, "stdout"):
      self.stdout.close()
    self.stderr.close()

def readStandardStream(inFile, outFile):
  for readBytes in iter(inFile.read, b""):
    outFile.write(readBytes.decode())

class ProcessSpecFixture(SibtSpecFixture):
  def __init__(self, tmpdir, capfd):
    super().__init__(tmpdir, capfd)
    self.processStartedSignal = threading.Event()
    self.finishedPid = None
    self.actions = []

  def useActualSibtConfig(self):
    for dest in [
        self.paths.readonlySchedulersDir, 
        self.paths.readonlySynchronizersDir, 
        self.paths.runnersDir]:
      shutil.copytree(relativeToProjectRoot("sibt/" + os.path.basename(dest)), 
        dest)

  def _buildSibtCall(self):
    return [relativeToProjectRoot("sibt/sibt"),
        "--config-dir", self.paths.configDir,
        "--var-dir", self.paths.varDir,
        "--readonly-dir", self.paths.readonlyDir,
        "--no-sys-config",
        "--utc"]

  def startSibtProcess(self, *args):
    return ForkExecSubProcess(self._buildSibtCall() + list(args), False, False)

  def runSibtAsAProcess(self, *args, blockingStdout=False, 
      stdoutReadFdClosed=False):
    self.processStartedSignal.clear()
    startTime = time.perf_counter()
    stdoutBuffer = io.StringIO()
    stderrBuffer = io.StringIO()
    readStdout = not blockingStdout and not stdoutReadFdClosed

    with ForkExecSubProcess(self._buildSibtCall() + list(args), 
        blockingStdout, stdoutReadFdClosed) as process:
      self.processGroupId = process.pid
      self.processStartedSignal.set()
      stderrReader = threading.Thread(target=readStandardStream,
          args=(process.stderr, stderrBuffer))
      stderrReader.start()
      if readStdout:
        stdoutReader = threading.Thread(target=readStandardStream,
            args=(process.stdout, stdoutBuffer))
        stdoutReader.start()
      process.wait()

      if readStdout:
        stdoutReader.join()
      stderrReader.join()

    self.result = RunResult(strToTest(stdoutBuffer.getvalue()), 
        strToTest(stderrBuffer.getvalue()), process.returncode)
    sys.stdout.write(stdoutBuffer.getvalue())
    sys.stderr.write(stderrBuffer.getvalue())
    self.finishedPid = process.pid
    self.secondsElapsedWhileRunning = time.perf_counter() - startTime

  def afterSeconds(self, seconds, func):
    self.processStartedSignal.clear()
    def threadMain():
      self.processStartedSignal.wait()
      pid = self.processGroupId
      time.sleep(seconds)
      if self.finishedPid == pid:
        return
      func()
    thread = threading.Thread(target=threadMain, daemon=True)
    thread.start()
    self.actions.append(thread)

  def shouldNotHaveTakenMoreSecondsThan(self, maxSeconds):
    assert self.secondsElapsedWhileRunning < maxSeconds

  def sigIntToProcessGroup(self):
    os.killpg(self.processGroupId, signal.SIGINT)
  def sigTermToProcessGroup(self):
    os.killpg(self.processGroupId, signal.SIGTERM)
  def singleSigTermToSibt(self):
    os.kill(self.processGroupId, signal.SIGTERM)

  def sigKill(self):
    os.killpg(self.processGroupId, signal.SIGKILL)

  def shouldHaveExitedFromSignal(self, signalNumber):
    assert self.result.exitStatus == -signalNumber

@pytest.fixture
def fixture(tmpdir, capfd):
  return ProcessSpecFixture(tmpdir, capfd)

def test_shouldBeAbleToHandleDoubleDashNames(fixture):
  fixture.useActualSibtConfig()
  poem = ("the unworthy are taken,\n"
      "our fall defies all logic;\n"
      "soothing melody\n")

  rule = fixture.conf.realRule("--rule", "anacron", "rdiff-backup").write()
  testFile = path.local(rule.loc1) / "--file"
  testFile.write(poem)

  fixture.runSibtAsAProcess("schedule", "--", "--rule")
  fixture.shouldHaveExitedWithStatus(0)

  fixture.runSibtAsAProcess("list-files", rule.loc1, ":")
  fixture.stdout.shouldContainLinePatterns("--file")

  testFile.write("blah")
  with path.local(rule.loc1).as_cwd():
    fixture.runSibtAsAProcess("restore", "--", "--file", ":")
  assert testFile.read() == poem

def test_shouldHandleSigIntAndTermWithWifsignaledAndAnErrorMessage(fixture):
  fixture.useActualSibtConfig()

  syncer = fixture.conf.aSyncer("infinite-list").withContent(r"""#!bash-runner
  versions-of() {
    echo 20
  }
  list-files() {
    trap 'echo from-syncer >&2; exit 1' INT TERM
    trap '' PIPE
    set +e
    moreThanPythonStdoutBuffer=10000

    echo -n file-
    head -c $moreThanPythonStdoutBuffer /dev/zero | tr -c '' a
    echo -n -e '\0'
    sleep 2
  }""").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  def check(sigFunc, signalName, signalNumber):
    fixture.afterSeconds(0.2, sigFunc) 
    fixture.runSibtAsAProcess("list-files", rule.loc1, ":")
    fixture.stdout.shouldContainLinePatterns("file-*")
    fixture.stderr.shouldInclude(signalName, "from-syncer").andAlso.\
        shouldNotInclude("Traceback", "error when calling")
    fixture.shouldHaveExitedFromSignal(signalNumber)

  check(fixture.sigIntToProcessGroup, "SIGINT", signal.SIGINT)
  check(fixture.singleSigTermToSibt, "SIGTERM", signal.SIGTERM)

def test_shouldStopAsapWhenGettingAFatalSignalDuringBusyCode(fixture):
  fixture.conf.ruleWithSchedAndSyncer("foo").write()

  fixture.afterSeconds(0.2, fixture.sigIntToProcessGroup)
  fixture.afterSeconds(2, fixture.sigKill)
  fixture.runSibtAsAProcess("li", blockingStdout=True)
  fixture.stderr.shouldInclude("SIGINT")
  fixture.shouldNotHaveTakenMoreSecondsThan(0.5)
  fixture.shouldHaveExitedFromSignal(signal.SIGINT)

def test_shouldLetSyncersDecideHowToActOnSignalsAndWaitForThem(fixture):
  fixture.useActualSibtConfig()

  syncer = fixture.conf.aSyncer("takes-time").withContent(r"""#!bash-runner
  sync() {
    trap '
    trap "" TERM
    sleep 0.1
    echo syncer-cleaned-up >&2
    trap - TERM
    kill $$' TERM
    sleep 3
  }""").write()

  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  fixture.afterSeconds(0.3, fixture.sigTermToProcessGroup)
  fixture.runSibtAsAProcess("sync", rule.name)
  fixture.stderr.shouldInclude("syncer-cleaned-up", "SIGTERM").andAlso.\
      shouldIncludeInOrder("rule", rule.name, "failed", "-15")

def test_shouldNotOutputAnyErrorsWhenGettingSigpipe(fixture):
  fixture.conf.ruleWithSchedAndSyncer("rule").write()

  fixture.runSibtAsAProcess("li", stdoutReadFdClosed=True)
  fixture.stderr.shouldNotInclude("Traceback", "pipe")
  fixture.shouldHaveExitedFromSignal(signal.SIGPIPE)

def test_shouldKeepIgnoringSignalsItsParentIgnored(fixture):
  fixture.useActualSibtConfig()
  syncer = fixture.conf.aSyncer().withContent(r"""#!bash-runner
  sync() {
    sleep 2
  }""").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()

  fixture.afterSeconds(0.2, fixture.sigTermToProcessGroup)
  fixture.afterSeconds(0.3, fixture.sigKill)
  with SigHandler(signal.SIGTERM, signal.SIG_IGN):
    fixture.runSibtAsAProcess("sync", rule.name)

  fixture.stderr.shouldBeEmpty()
  fixture.shouldHaveExitedFromSignal(signal.SIGKILL)

def test_shouldFinishLoggingSchedulingStatisticsEvenIfSignaled(fixture):
  flagFile = fixture.tmpdir / "flag"

  syncer = fixture.conf.aSyncer("blocking").withContent(r"""#!/usr/bin/env bash
  if [ "$1" = sync ]; then
    trap 'sleep 0.1; echo trapped; exit 1' INT
    echo foo
    sleep 3
  else
    exit 200
  fi
  """).write()

  logFile = fixture.tmpdir / "logfile"
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).withSchedOpts(
      ExecOnFailure="touch {0}".format(flagFile), LogFile=str(logFile)).write()

  fixture.afterSeconds(0.3, fixture.sigIntToProcessGroup)
  fixture.runSibtAsAProcess("execute-rule", rule.name)

  from sibt.api import openLog

  logging = None
  for i in range(100):
    time.sleep(0.05)
    logging = openLog(fixture.paths, sibtSysPaths=None).loggingsOfRules(
        "*")[rule.name][0]
    if logging.finished:
      break

  assert logging.finished
  assert not logging.succeeded
  strToTest(logging.output).shouldInclude(
      "foo\ntrapped\n", "SIGINT")

  assert os.path.isfile(str(flagFile))

def test_shouldExitFromSignalsWhenExecutingARule(fixture):
  sched = fixture.conf.aSched().withExecuteFuncCode(r"""
    def execute(execEnv, scheduling):
      execEnv.logSubProcess("sleep 10", shell=True)
      return execEnv.runSynchronizer()""").write()

  rule = fixture.conf.ruleWithSyncer().withScheduler(sched).write()

  fixture.afterSeconds(0.3, fixture.sigIntToProcessGroup)
  fixture.runSibtAsAProcess("execute-rule", rule.name)

  fixture.shouldHaveExitedFromSignal(signal.SIGINT)
  fixture.shouldNotHaveTakenMoreSecondsThan(1)

def test_shouldNotAllowSyncingTwoRulesAtTheSameTime(fixture):
  syncer = fixture.conf.aSyncer().withContent(r"""#!/usr/bin/env bash
  if [ "$1" = sync ]; then
    sleep 3
  else exit 200; fi""").write()
  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).write()
  
  with fixture.startSibtProcess("sync", rule.name):
    time.sleep(0.2)
    fixture.runSibtAsAProcess("sync", rule.name)
    fixture.shouldNotHaveTakenMoreSecondsThan(0.5)
    fixture.shouldHaveExitedWithStatus(1)
    fixture.stderr.shouldIncludeInOrder("could not", "lock",
        "running", "failed")
