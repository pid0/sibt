import pytest
from test.integration.synchronizers import loadSynchronizer
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException
from test.common.builders import anyUTCDateTime
from test.common.assertutil import iterToTest

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.synchronizerCounter = 0

  def loadSynchronizerWithCode(self, code):
    path = self.tmpdir.join("syncer-" + str(self.synchronizerCounter))
    path.write(code)
    path.chmod(0o700)
    return loadSynchronizer(str(path))

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class RunnerTest(object):
  def loadSynchronizerWithCode(self, code, fixture):
    return fixture.loadSynchronizerWithCode(
        "#!{0}\n".format(self.runnerName) + code)

  def assertFailureWithSyncCode(self, code, fixture):
    syncer = self.loadSynchronizerWithCode(code, fixture)
    with pytest.raises(ExternalFailureException) as ex:
      syncer.sync(dict())
    return ex.value

  def test_shouldNotFailForFunctionsThatHaveAReasonableDefault(self, fixture):
    syncer = self.loadSynchronizerWithCode("", fixture)
    assert syncer.onePortMustHaveFileProtocol == False
    _ = syncer.availableOptions
    iterToTest(syncer.ports).shouldContainMatching(
        lambda port: port.supportedProtocols == ["file"] and \
            not port.isWrittenTo,
        lambda port: port.supportedProtocols == ["file"] and port.isWrittenTo)
    assert syncer.versionsOf("/mnt/data/bar", 1, dict()) == []

  def test_shouldThrowExceptionForNonTrivialNotImplementedFunctions(self, 
      fixture):
    syncer = self.loadSynchronizerWithCode("", fixture)
    with pytest.raises(SynchronizerFuncNotImplementedException):
      syncer.listFiles("/tmp/file", 1, anyUTCDateTime(), False, dict())
    with pytest.raises(SynchronizerFuncNotImplementedException):
      syncer.sync(dict())

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
