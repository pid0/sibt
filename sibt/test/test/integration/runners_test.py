import pytest
from test.integration.interpreters import loadInterpreter
from sibt.infrastructure.interpreterfuncnotimplementedexception \
    import InterpreterFuncNotImplementedException
from sibt.infrastructure.externalfailureexception \
    import ExternalFailureException
from test.common.builders import anyUTCDateTime

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.interpreterCounter = 0

  def loadInterpreterWithCode(self, code):
    path = self.tmpdir.join("inter-" + str(self.interpreterCounter))
    path.write(code)
    path.chmod(0o700)
    return loadInterpreter(str(path))

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class RunnerTest(object):
  def loadInterpreterWithCode(self, code, fixture):
    return fixture.loadInterpreterWithCode(
        "#!{0}\n".format(self.runnerName) + code)

  def assertFailureWithSyncCode(self, code, fixture):
    inter = self.loadInterpreterWithCode(code, fixture)
    with pytest.raises(ExternalFailureException) as ex:
      inter.sync(dict())
    return ex.value

  def test_shouldNotFailForFunctionsThatHaveAReasonableDefault(self, fixture):
    inter = self.loadInterpreterWithCode("", fixture)
    assert inter.availableOptions == []
    assert inter.writeLocIndices == [2]
    assert inter.versionsOf("/mnt/data/bar", 1, dict()) == []

  def test_shouldThrowExceptionForNonTrivialNotImplementedFunctions(self, 
      fixture):
    inter = self.loadInterpreterWithCode("", fixture)
    with pytest.raises(InterpreterFuncNotImplementedException):
      inter.listFiles("/tmp/file", 1, anyUTCDateTime(), False, dict())
    with pytest.raises(InterpreterFuncNotImplementedException):
      inter.sync(dict())

  def test_shouldFailIndicatingCorrectExitStatusIfSomeSubcommandFails(self,
      fixture):
    exitStatus = 5
    ex = self.assertFailureWithSyncCode(self.syncCodeWithFailingSubcommand(
      exitStatus), fixture)
    assert ex.exitStatus == exitStatus

class Test_BashRunnerTest(RunnerTest):
  @property
  def runnerName(self):
    return "bash-runner"
  def syncCodeWithFailingSubcommand(self, exitStatus):
    return """sync() {{
        (echo rsync; exit {0})
        echo finished
      }}""".format(exitStatus)

  def test_shouldFailIfUnsetVariableIsUsed(self, fixture):
    self.assertFailureWithSyncCode("""
      sync() {
        echo $blah
      }""", fixture)

  def test_shouldFailIfSubcommandFailsWithinAPipe(self, fixture):
    self.assertFailureWithSyncCode("""
      sync() {
        (echo foo; exit 2) | cat
      }""", fixture)

class Test_PythonRunnerTest(RunnerTest):
  @property
  def runnerName(self):
    return "python-runner"
  def syncCodeWithFailingSubcommand(self, exitStatus):
    return """
import subprocess
def sync(**_):
  subprocess.check_call(["bash", "-c", "exit 5"])
        """

  def test_shouldHandleOtherExceptionsAsUsualByPrintingTraceAndExitingWith1(
      self, fixture, capfd):
    ex = self.assertFailureWithSyncCode("""
def sync(**_):
  raise Exception("foo")""", fixture)
    assert ex.exitStatus == 1

    _, stderr = capfd.readouterr()
    assert "foo" in stderr
    assert "sync" in stderr
