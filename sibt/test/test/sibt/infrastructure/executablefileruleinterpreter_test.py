import pytest
import os
from sibt.configuration.exceptions import ConfigConsistencyException
from test.common.execmock import ExecMock
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir

  def _create(self, filePath, fileName):
    execs = ExecMock()
    return (ExecutableFileRuleInterpreter.createWithFile(
        str(filePath), fileName, execs), execs)
  def createWithExecutable(self, name):
    path = self.tmpdir.join(name)
    path.write("#!/usr/bin/env bash")
    self.lastPath = str(path)
    os.chmod(str(path), 0o700)

    return self._create(path, name)
  def lastInterpreterCall(self, args, result):
    return (self.lastPath, args, result)
  def createWithRegularFile(self, name):
    path = self.tmpdir.join(name)
    path.write("foo")
    return self._create(path, name)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldUseFileNameAsName(fixture):
  name = "some-interpreter"
  interpreter, _ = fixture.createWithExecutable(name)
  assert interpreter.name == name

def test_shouldThrowExceptionIfCreatedWithNotExecutableFile(fixture):
  with pytest.raises(ConfigConsistencyException):
    interpreter = fixture.createWithRegularFile("wont-work")

def test_shouldCallExecutableWithOptionsInKeyValueFormatIfToldToSync(fixture):
  ruleName = "some-rule-name"
  options = {"First": "foo", "Second": "/tmp/quux"}

  interpreter, execs = fixture.createWithExecutable("bar")
  execs.expectCalls(fixture.lastInterpreterCall(
    lambda args: args[0] == "sync" and set(args[1:3]) == 
        set(["First=foo", "Second=/tmp/quux"]) and len(args) == 3, ""))

  interpreter.sync(options)

  execs.check()

def test_shouldReturnEachLineOfOutputAsAnAvailableOption(fixture):
  interpreter, execs = fixture.createWithExecutable("foo")

  execs.expectCalls(fixture.lastInterpreterCall(
    ("available-options",), "A\nB\n\nC\n"))

  assert interpreter.availableOptions == ["A", "B", "C"]
  execs.check()
  

