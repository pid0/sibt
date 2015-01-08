import pytest
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.runner = SynchronousProcessRunner()
    self.counter = 0

  def writeBashExecutable(self, code):
    self.counter += 1
    path = self.tmpdir.join("script-{0}".format(self.counter))
    path.write("#!/usr/bin/env bash\n" + code)
    path.chmod(0o700)
    return str(path)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldReturnIterableContainingTheLinesSplitAtSpecifiedChar(fixture):
  path = fixture.writeBashExecutable(r"""
      echo -n ' foo'; echo -n -e '\0'
      echo -n bar; if [ "$1" != leave-off-last-null ]; then 
        echo -n -e '\0'; fi""")

  expectedOutput = [" foo", "bar"]

  assert list(fixture.runner.getOutput(path, delimiter="\0")) == expectedOutput
  assert list(fixture.runner.getOutput(path, "leave-off-last-null", 
      delimiter="\0")) == expectedOutput

def test_shouldReturnEmptyIterableForNoOutput(fixture):
  path = fixture.writeBashExecutable("")

  assert list(fixture.runner.getOutput(path)) == []

def test_shouldRaiseCustomExceptionIfProgramReturnsWithNonZeroStatus(fixture):
  path = fixture.writeBashExecutable(r"""
      echo out
      exit 103""")

  with pytest.raises(ExternalFailureException) as ex:
    assert fixture.runner.getOutput(path) == ["out"]
  assert ex.value.exitStatus == 103


