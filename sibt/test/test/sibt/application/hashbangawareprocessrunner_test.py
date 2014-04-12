import pytest
from test.common import mock
from sibt.application.hashbangawareprocessrunner import \
    HashbangAwareProcessRunner
from test.common.builders import existingRunner

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir

  def construct(self, runners=[]):
    wrapped = mock.mock()
    return wrapped, HashbangAwareProcessRunner(runners, wrapped)

  def writeExecutable(self, contents):
    path = self.tmpdir.join("executable")
    path.write(contents)
    path.chmod(0o700)
    return str(path)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldForwardGetOutputAndExecuteCallsToWrappedRunner(fixture):
  returnValue = "the bag"

  wrapped, runner = fixture.construct()

  wrapped.expectCallsInOrder(mock.call("getOutput", ("file", "1", "2"), 
      returnValue))
  assert runner.getOutput("file", "1", "2") == returnValue
  wrapped.checkExpectedCalls()

  wrapped.expectCallsInOrder(mock.call("execute", ("executable", "foo"), 
      None))
  runner.execute("executable", "foo") 
  wrapped.checkExpectedCalls()

def test_shouldPrependRunnerToArgsIfHashbangLineMatchesRunnerName(fixture):
  firstRunnerPath, firstRunner = existingRunner(fixture.tmpdir, "runner1")
  _, secondRunner = existingRunner(fixture.tmpdir, "second-runner")
  runners = [secondRunner, firstRunner]

  wrapped, runner = fixture.construct(runners)
  executable = fixture.writeExecutable("#!runner1\necho foo")

  def checkMethod(methodName):
    wrapped.expectCallsInOrder(mock.call(methodName, 
        (firstRunnerPath, executable, "one", "two"), ""))
    if methodName == "execute":
      runner.execute(executable, "one", "two")
    else:
      runner.getOutput(executable, "one", "two")
    wrapped.checkExpectedCalls()

  checkMethod("execute")
  checkMethod("getOutput")




