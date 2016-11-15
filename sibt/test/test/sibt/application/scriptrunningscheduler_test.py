import pytest
from sibt.application.scriptrunningscheduler import ScriptRunningScheduler
from test.sibt.application.intermediateschedulertest import \
    IntermediateSchedulerTestFixture
from test.common.bufferinglogger import BufferingLogger
from test.common.builders import mockSched, buildScheduling, execEnvironment
from test.common.assertutil import strToTest, iterToTest
from test.common import mock
import os
import functools

class ExceptionForTesting(BaseException):
  pass
def raiseTestException():
  raise ExceptionForTesting()

def call(execOptionId, exitCode=0, sideEffect=None, environmentVars=None):
  return (execOptionId, exitCode, sideEffect, environmentVars)

class FailingLogger(object):
  def write(self, chunk, **kargs):
    raiseTestException()
  def close():
    raiseTestException()

AllExecs = ["before", "failure", "success"]
class Fixture(IntermediateSchedulerTestFixture):
  def __init__(self):
    self.callsMock = mock.mock()
    self.logger = BufferingLogger()

  def _callMatcher(self, expectedProgram, expectedEnvVars,
      program, environmentVars=None, **kwargs):
    if program != expectedProgram:
      return False

    if expectedEnvVars is not None:
      for key, value in expectedEnvVars.items():
        if environmentVars[key] != value:
          return False
  
    return True

  def expectCalls(self, *expectations):
    calls = [
        mock.callMatching("call", functools.partial(self._callMatcher, 
          expectedProgram, envVars), ret=exitCode, sideEffectFunc=sideEffect) 
        for expectedProgram, exitCode, sideEffect, envVars in expectations]
    self.callsMock.expectCallsInOrder(*calls)

  def _logSubProcessWith(self, logger, *args, **kwargs):
    return self.callsMock.call(*args, **kwargs)

  def _subExecute(self, *args):
    return self.callsMock.call("execute") == 0

  def _optionsFromExecs(self, execs):
    ret = dict()
    namesToOptions = dict(
        before="ExecBefore",
        failure="ExecOnFailure",
        success="ExecOnSuccess")

    for execOptName in execs:
      ret[namesToOptions[execOptName]] = execOptName

    return ret

  def construct(self, wrappedSched):
    return ScriptRunningScheduler(wrappedSched)
  
  def execute(self, execs, ruleName=None):
    execEnv = execEnvironment(
        logger=self.logger,
        logSubProcessWith=self._logSubProcessWith)

    scheduler = self.makeSched(subExecute=self._subExecute)
    try:
      ret = scheduler.execute(execEnv, 
          buildScheduling(ruleName=ruleName, **self._optionsFromExecs(execs)))
    finally:
      self.callsMock.checkExpectedCalls()
      self.callsMock.clearExpectedCalls()
    return ret

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldLogFailureOfExecOnFailure(fixture):
  execs = ["success", "failure"]

  fixture.expectCalls(
      call("execute", 1),
      call("failure", 22))

  assert fixture.execute(execs) == False
  fixture.logger.decoded.shouldInclude("ExecOnFailure", "failed", "22")

  fixture.logger.clear()
  fixture.expectCalls(
      call("execute", 1),
      call("failure", 0))
  assert fixture.execute(execs) == False
  fixture.logger.decoded.shouldBeEmpty()

def test_shouldExecuteExecBeforeAndExecOnSuccessIfEverythingIsOk(fixture):
  assert "ExecBefore" in fixture.optionNames
  assert "ExecOnSuccess" in fixture.optionNames

  fixture.expectCalls(
      call("before", environmentVars=dict(SIBT_RULE="foo")),
      call("execute"),
      call("success", environmentVars=dict(SIBT_RULE="foo")))

  assert fixture.execute(AllExecs, ruleName="foo") == True
  fixture.logger.decoded.shouldBeEmpty()

def test_shouldRunExecOnFailureAndFailExecutionIfExecOnSuccessFails(fixture):
  execs = ["success", "failure"]

  fixture.expectCalls(
      call("execute"),
      call("success", 5),
      call("failure"))

  assert fixture.execute(execs) == False
  fixture.logger.decoded.shouldInclude("ExecOnSuccess", "5")

def test_shouldRunExecOnFailureAndFailfExecBeforeFails(fixture):
  fixture.expectCalls(
      call("before", 1),
      call("failure"))

  assert fixture.execute(AllExecs) == False
  fixture.logger.decoded.shouldInclude("ExecBefore")

def test_shouldExecuteExecOnFailureIfAnInternalExceptionOccurs(fixture):
  fixture.expectCalls(
      call("execute", sideEffect=raiseTestException),
      call("failure"))
  with pytest.raises(ExceptionForTesting):
    fixture.execute(["success", "failure"])

  fixture.expectCalls(
      call("before", sideEffect=raiseTestException),
      call("failure"))
  with pytest.raises(ExceptionForTesting):
    fixture.execute(AllExecs)

  fixture.expectCalls(
      call("before"),
      call("execute"),
      call("success", sideEffect=raiseTestException),
      call("failure"))
  with pytest.raises(ExceptionForTesting):
    fixture.execute(AllExecs)

def test_shouldCheckSyntaxOfScriptsWithoutExecutingThem(fixture, tmpdir):
  flagFile = str(tmpdir / "flag")

  erroneousCode = "touch {0}\n(echo foo".format(flagFile)

  schedulings = [
      buildScheduling("touching", ExecOnFailure=erroneousCode),
      buildScheduling(ExecBefore="{")]

  iterToTest(fixture.check(schedulings)).shouldContainMatching(
      lambda error: strToTest(error).shouldInclude("unexpected", 
        "ExecOnFailure", "syntax", "touching"),
      lambda error: "ExecBefore" in error)
  assert not os.path.isfile(flagFile)

def test_shouldReturnTheWrappedSchedsCheckErrors(fixture):
  iterToTest(fixture.check([buildScheduling(ExecOnSuccess="(")], 
    subCheckErrors=["foo", "bar"])).shouldContainMatching(
        lambda error: "ExecOnSuccess" in error,
        lambda error: error == "foo",
        lambda error: error == "bar")
