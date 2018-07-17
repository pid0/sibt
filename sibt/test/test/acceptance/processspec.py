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

import pytest
from test.acceptance.sibtspec import SibtSpecFixture, decode
from py import path
from test.common import relativeToProjectRoot
from test.common.assertutil import strToTest, iterToTest
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

from test.common import sshserver
from test.common.sshserver import sshServerFixture

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
    self.returncode = None
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
  def sigIntToProcessGroup(self):
    os.killpg(self.pid, signal.SIGINT)

  def isRunning(self):
    pid, _ = os.waitpid(self.pid, os.WNOHANG)
    return pid == 0

  def __enter__(self):
    return self

  def __exit__(self, x, y, z):
    if hasattr(self, "stdout"):
      self.stdout.close()
    self.stderr.close()

def readStandardStream(inFile, outFile):
  for readBytes in iter(inFile.read, b""):
    outFile.write(decode(readBytes))

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
    fixture.afterSeconds(0.3, sigFunc) 
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

def test_shouldFinishLoggingExecutionStatisticsEvenIfSignaled(fixture):
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

  execution = None
  for i in range(100):
    time.sleep(0.05)
    execution = fixture.getSingleExecution(fixture.paths, None, rule.name)
    if execution.finished:
      break

  assert execution.finished
  assert not execution.succeeded
  strToTest(execution.output).shouldInclude(
      "foo\ntrapped\n", "SIGINT")

  assert os.path.isfile(str(flagFile))

def test_shouldFinishUnfinishedLoggedExecutionsAfterTheyHadToBeAbandoned(
    fixture):
  syncer = fixture.conf.aSyncer().withBashCode(r"""
    if [ "$1" = sync ]; then
      sleep 5
    else exit 200; fi""").write()
  rule = fixture.conf.ruleWithSched("foo").withSynchronizer(syncer).write()

  fixture.afterSeconds(0.3, fixture.sigKill)
  fixture.runSibtAsAProcess("execute-rule", rule.name)

  execution = fixture.getSingleExecution(fixture.paths, None, rule.name)
  assert execution.finished
  assert not execution.succeeded
  strToTest(execution.output).shouldIncludeInOrder("error", "not", "finished")

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

def test_shouldNotAllowExecutingOrSchedulingARuleIfItIsAlreadyExecuting(
    fixture):
  sched = fixture.conf.aSched().withExecuteFuncCode(r"""
    def execute(*args):
      import time; time.sleep(3); return True""").write()
  rule = fixture.conf.ruleWithSyncer().withScheduler(sched).write()
  
  with fixture.startSibtProcess("execute-rule", rule.name):
    time.sleep(0.2)
    assert not fixture.getSingleExecution(fixture.paths, None, 
        rule.name).finished

    fixture.runSibtAsAProcess("--verbose", "execute-rule", rule.name)
    fixture.shouldNotHaveTakenMoreSecondsThan(0.5)
    fixture.shouldHaveExitedWithStatus(4)
    fixture.stderr.shouldIncludeInOrder("already", "could not", "lock")

    fixture.runSibtAsAProcess("schedule", rule.name)
    fixture.shouldHaveExitedWithStatus(4)
    fixture.stderr.shouldInclude(rule.name, "currently executing")

def test_shouldWaitForExecutionAfterSignalWhenUsingSimpleSched(fixture):
  fixture.useActualSibtConfig()
  syncer = fixture.conf.aSyncer().withBashCode(r"""
    if [ "$1" = sync ]; then
      trap '' INT
      sleep 5
    else exit 200; fi""").write()
  rule = fixture.conf.realRule("foo", "simple", syncer.name).write()

  with fixture.startSibtProcess("schedule", "foo") as sibtProcess:
    time.sleep(0.6)
    sibtProcess.sigIntToProcessGroup()
    time.sleep(0.1)
    assert sibtProcess.isRunning()
    assert b"Waiting" in sibtProcess.stderr.read1(1024)
    sibtProcess.sigIntToProcessGroup()
    time.sleep(0.1)
    assert sibtProcess.wait() == -signal.SIGINT

def test_shouldEfficientlyCollectVersionsFromSyncers(fixture):
  syncer = fixture.conf.aSyncer().withBashCode(r"""
    if [ "$1" = versions-of ]; then
      sleep 0.2
      echo 0
    else
      exit 200
    fi""").write()

  rules = [fixture.conf.ruleWithSched().withSynchronizer(syncer).\
      withLoc1("/foobar").write() for _ in range(20)]

  fixture.runSibtAsAProcess("versions-of", "/foobar")
  assert len(fixture.stdout.lines()) == 20
  fixture.shouldNotHaveTakenMoreSecondsThan(0.8)

def test_shouldAutomaticallyMountViaSSHIfTheSyncerDoesntSupportIt(
    fixture, sshServerFixture):
  fixture.useActualSibtConfig()
  loc2PathFile = fixture.tmpdir / "loc2Path"

  syncer = fixture.conf.aSyncer().withCode(r"""#!bash-runner
    versions-of() {
      echo 0
    }
    list-files() {
      echo -n file1
      echo -n -e '\0'
      echo -n file2
      echo -n -e '\0'

      echo -n "$Loc2Path" >'{0}'
      mkdir "$Loc2Path"/'TITAN!' || true
    }""".replace("{0}", str(loc2PathFile))).write()

  rule = fixture.conf.ruleWithSched().withSynchronizer(syncer).\
      withNewValidLocs().withSyncerOpts(
          RemoteShellCommand=sshServerFixture.remoteShellCommand)
  initialLoc2 = str(rule.loc2)
  rule = rule.withLoc2("ssh://localhost:{0}{1}".format(
    sshserver.Port, initialLoc2)).write()

  fixture.runSibtAsAProcess("list-files", rule.loc1, ":")
  fixture.shouldHaveExitedWithStatus(0)
  fixture.stdout.shouldInclude("file2")

  sftpServer = sshserver.LastSFTPHandler
  iterToTest(sftpServer.actions).shouldIncludeMatching(lambda action:
      action[0] == "mkdir" and action[1].endswith("/TITAN!"))

  assert os.path.lexists(initialLoc2)
  assert not os.path.lexists(loc2PathFile.read())
