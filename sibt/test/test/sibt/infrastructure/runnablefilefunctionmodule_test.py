import pytest
import os
from sibt.infrastructure.runnablefilefunctionmodule import \
    RunnableFileFunctionModule
from test.common.execmock import ExecMock
from test.common import execmock
from test.common.assertutil import FakeException
from sibt.infrastructure.exceptions import ExternalFailureException, \
    ModuleFunctionNotImplementedException
from functools import partial

class Fixture(object):
  def __init__(self):
    self.executablePath = "/tmp/foo"
    self.functions, self.execs = self._create(self.executablePath)

  def _create(self, filePath):
    execs = ExecMock()
    return (RunnableFileFunctionModule(execs, str(filePath)), execs)

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldCallExecutableWithOptionsInKeyValueFormat(fixture):
  options = {"First": "foo", "Second": "/tmp/quux"}

  fixture.execs.expect(fixture.executablePath, execmock.call(
      lambda args: args[0] == "sync" and args[1] == "arg" and set(args[2:4]) == 
          set(["First=foo", "Second=/tmp/quux"]) and len(args) == 4))

  fixture.functions.callVoid("sync", ["arg"], options)

  fixture.execs.check()

def test_shouldRemoveEmptyLinesAndSurroundingWhitespaceFromFuzzyOutput(fixture):
  fixture.execs.expect(fixture.executablePath, execmock.call(
    ("all-fuzzy",), ret=["A ", "B", " ", " C  D"]))

  assert fixture.functions.callFuzzy("all-fuzzy", [], {}) == ["A", "B", "C  D"]

  fixture.execs.check()

def test_shouldSplitLinesOfExactOutputAtNullBytes(fixture):
  uniterableOutput = object()

  fixture.execs.expect(fixture.executablePath, execmock.call(("list-files",), 
    ret=uniterableOutput, delimiter="\0"))

  assert fixture.functions.callExact("list-files", [], {}) is uniterableOutput

  fixture.execs.check()

def test_shouldThrowNotImplementedExceptionIffExecutableReturns200(fixture):
  def failWithExitStatus(exitStatus, *args):
    raise ExternalFailureException("", [], exitStatus)

  def checkExceptionTypeWithExitStatus(exceptionType, exitStatus):
    fixture.execs.expect(fixture.executablePath, 
        execmock.call(partial(failWithExitStatus, exitStatus)))
    with pytest.raises(exceptionType):
      fixture.functions.callVoid("foo", [], {})
  
  checkExceptionTypeWithExitStatus(ModuleFunctionNotImplementedException, 200)
  fixture.execs.reset()
  checkExceptionTypeWithExitStatus(ExternalFailureException, 1)
