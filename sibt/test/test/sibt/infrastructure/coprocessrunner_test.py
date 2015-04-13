import pytest
from sibt.infrastructure.coprocessrunner import \
    CoprocessRunner
from sibt.infrastructure.exceptions import ExternalFailureException

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.runner = CoprocessRunner()
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

@pytest.mark.parametrize("arg", ["leave-off-last-null", ""])
def test_shouldReturnIteratorContainingTheLinesSplitAtSpecifiedChar(arg, 
    fixture):
  path = fixture.writeBashExecutable(r"""
      echo -n -e ' foo\0'
      echo -n bar; if [ "$1" != leave-off-last-null ]; then 
        echo -n -e '\0'; fi""")

  assert list(fixture.runner.getOutput(path, arg, delimiter="\0")) == \
      [" foo", "bar"]

def test_shouldWorkInAllTimingDependentCircumstances(fixture):
  path = fixture.writeBashExecutable(r"echo -n -e 'a\nb\n'")

  assert list(fixture.runner.getOutput(path)) == ["a", "b"]

  path = fixture.writeBashExecutable(r"""for i in $(seq 5000); do 
    echo -n 12345
  done 
  echo""")

  assert list(fixture.runner.getOutput(path)) == [5000 * "12345"]

def test_shouldReturnEmptyIteratorForNoOutput(fixture):
  path = fixture.writeBashExecutable("")

  assert list(fixture.runner.getOutput(path)) == []

def test_shouldRaiseCustomExceptionIfProgramReturnsWithNonZeroStatus(fixture):
  path = fixture.writeBashExecutable(r"""
      echo out
      sleep 0.1
      exit 103""")

  with pytest.raises(ExternalFailureException) as ex:
    list(fixture.runner.getOutput(path))
  assert ex.value.exitStatus == 103

def test_shouldRaiseExceptionDuringGetOutputCallIfProgramFailsWithoutOutput(
    fixture):
  path = fixture.writeBashExecutable(r"exit 54")

  with pytest.raises(ExternalFailureException) as ex:
    fixture.runner.getOutput(path)
  assert ex.value.exitStatus == 54
