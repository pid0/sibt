from test.common.rulebuilder import anyRule
import pytest
import os
from test.common.executionlogger import ExecutionLogger
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.processLogger = ExecutionLogger()

  def _create(self, filePath, fileName):
    return ExecutableFileRuleInterpreter.createWithFile(
        str(filePath), fileName, self.processLogger)
  def shouldRunInterpreterWithExactlyTheseArguments(self, expectedArgLists):
    expectedPrograms = [(self.filePath, args) for args in expectedArgLists]
    assert self.processLogger.programsList == expectedPrograms
  def createWithExecutable(self, name):
    path = self.tmpdir.join(name)
    path.write("#!/usr/bin/env bash")
    self.filePath = str(path)
    os.chmod(str(path), 0o700)

    return self._create(path, name)
  def createWithRegularFile(self, name):
    path = self.tmpdir.join(name)
    path.write("foo")
    return self._create(path, name)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldUseFileNameAsName(fixture):
  name = "some-interpreter"
  interpreter = fixture.createWithExecutable(name)
  assert interpreter.name == name

def test_shouldThrowExceptionIfCreatedWithNotExecutableFile(fixture):
  with pytest.raises(Exception):
    interpreter = fixture.createWithRegularFile("wont-work")

def test_shouldCallExecutableWithRuleNameIfToldToSync(fixture):
  ruleName = "some-rule-name"

  interpreter = fixture.createWithExecutable("bar")
  interpreter.sync(anyRule().withName(ruleName).build())

  fixture.shouldRunInterpreterWithExactlyTheseArguments([(ruleName,)])
  

