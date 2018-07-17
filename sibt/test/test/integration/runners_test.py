import pytest
from test.integration.synchronizers import loadSynchronizer
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException
from test.common.builders import anyUTCDateTime, mkSyncerOpts
from test.common.assertutil import iterToTest
from test.integration.bashfunctestfixture import BashFuncTestFixture
from test.common import relativeToProjectRoot

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
      syncer.sync(mkSyncerOpts())
    return ex.value

  def test_shouldNotFailForFunctionsThatHaveAReasonableDefault(self, fixture):
    syncer = self.loadSynchronizerWithCode("", fixture)
    assert syncer.onePortMustHaveFileProtocol == False
    _ = syncer.availableOptions
    iterToTest(syncer.ports).shouldContainMatching(
        lambda port: "file" in port.supportedProtocols and \
            not port.isWrittenTo,
        lambda port: "file" in port.supportedProtocols and port.isWrittenTo)
    assert syncer.versionsOf(mkSyncerOpts(), "/mnt/data/bar", 1) == []
    assert syncer.check(mkSyncerOpts()) == []

  def test_shouldThrowExceptionForNonTrivialNotImplementedFunctions(self, 
      fixture):
    syncer = self.loadSynchronizerWithCode("", fixture)
    with pytest.raises(SynchronizerFuncNotImplementedException):
      syncer.listFiles(mkSyncerOpts(), lambda *_: None, "/tmp/file", 1, 
          anyUTCDateTime(), False)
    with pytest.raises(SynchronizerFuncNotImplementedException):
      syncer.sync(mkSyncerOpts())

  def test_shouldFailIndicatingCorrectExitStatusIfSomeSubcommandFails(self,
      fixture):
    exitStatus = 5
    ex = self.assertFailureWithSyncCode(self.syncCodeWithFailingSubcommand(
      exitStatus), fixture)
    assert ex.exitStatus == exitStatus

@pytest.fixture
def bashFuncFixture():
  return BashFuncTestFixture(relativeToProjectRoot(
    "sibt/runners/bash-runner"), "/dev/null ''")

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
 
  def test_shouldBeAbleToTestIfAPathIsWithinAnother(self, bashFuncFixture):
    def startsWithPath(path, prefix):
      return bashFuncFixture.compute("""
        if starts-with-path '{0}' '{1}'; then
          echo 1
        else
          echo 0
        fi""".format(path, prefix)) == b"1\n"

    assert startsWithPath("foo/bar", "foo")
    assert not startsWithPath("foobar", "foo")
    assert startsWithPath("foo", "foo")

  def test_shouldBeAbleToExtractTheChildPathsOfFilesInACommonFolder(
      self, bashFuncFixture):
    def toChildren(folderPath, paths):
      return bashFuncFixture.compute("to-children-of '{0}'".format(folderPath),
          input=paths)

    assert toChildren("folder",
        b"top\0"
        b"anothertoplevelfile\0"
        b"folder/\0"
        b"folder/file1\0"
        b"folder2/file2\0"
        b"folder/deeper/file3\0") == b"file1\0deeper/file3\0"

    assert toChildren("sub/actually-a-file",
        b"sub/actually-a-file\0") == b"actually-a-file\0"

    assert toChildren(".*",
        b".*/file1\0"
        b"sub/file2\0") == b"file1\0"

    assert toChildren("",
        b"file\0") == b"file\0"

    assert toChildren("\n\t",
        b"\n\t/foo\0") == b"foo\0"

  def test_shouldBeAbleToFilterPathsWithMoreThanOneComponent(
      self, bashFuncFixture):
    def removeNonTopLevelPaths(paths):
      return bashFuncFixture.compute("remove-non-top-level-paths", input=paths)

    assert removeNonTopLevelPaths(
        b"home/\0"
        b"home/user/file\0"
        b"file\0"
        b"usr/local/\0") == b"home/\0file\0"

  def test_shouldBeAbleToFilterTheTypeOfAFileFromAFileListing(
      self, bashFuncFixture):
    listing = (
        b"paris/latin-quarter/\0"
        b"paris/latin-quarter/cecile\0"
        b"leonore\n[\0"
        b"paris/latin-quarter/valentine\0")

    def filterFileType(filePath):
      return bashFuncFixture.compute("filter-file-type '{0}'".format(filePath),
          input=listing)
    
    assert filterFileType("sylvia") == b"missing\n"
    assert filterFileType("paris/latin-quarter/valentine") == b"non-directory\n"
    assert filterFileType("paris/latin-quarter") == b"directory\n"
    assert filterFileType("leonore\n[") == b"non-directory\n"

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
