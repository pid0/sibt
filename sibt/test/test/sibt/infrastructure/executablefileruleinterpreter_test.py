import pytest
import os
from sibt.configuration.exceptions import ConfigConsistencyException
from test.common.execmock import ExecMock
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from test.common.assertutil import iterableContainsInAnyOrder
from datetime import datetime, timezone

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir

  def _create(self, filePath, fileName):
    execs = ExecMock()
    return (ExecutableFileRuleInterpreter.createWithFile(
        str(filePath), fileName, execs), execs)
  def createWithExecutable(self, name="some-inter"):
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

def test_shouldCallExecutableWithOptionsInKeyValueFormat(fixture):
  options = {"First": "foo", "Second": "/tmp/quux"}

  interpreter, execs = fixture.createWithExecutable()
  execs.expectMatchingCalls(fixture.lastInterpreterCall(
      lambda args: args[0] == "sync" and set(args[1:3]) == 
          set(["First=foo", "Second=/tmp/quux"]) and len(args) == 3, ""))

  interpreter.sync(options)

  execs.check()

def test_shouldReturnEachNonEmptyLineOfOutputAsAnAvailableOption(fixture):
  interpreter, execs = fixture.createWithExecutable()

  execs.expectCalls(fixture.lastInterpreterCall(
    ("available-options",), "A \nB\n \nC\n"))

  assert interpreter.availableOptions == ["A", "B", "C"]
  execs.check()

def test_shouldParseUnixTimestampsAndW3CDateTimesAsVersions(fixture):
  inter, execs = fixture.createWithExecutable()
  path = "/etc/config"

  execs.expectMatchingCalls(fixture.lastInterpreterCall(
      lambda args: args[0] == "versions-of" and args[1] == "/etc/config" and 
      args[2] == "2" and args[3] == "Blah=quux", """
      250
      2013-05-10T13:05:20+03:00
      2014-12-05T05:13:00-02:00
      """))

  assert iterableContainsInAnyOrder(
      inter.versionsOf(path, 2, {"Blah": "quux"}),
      lambda time: time == datetime(1970, 1, 1, 0, 4, 10, 0, timezone.utc),
      lambda time: time == datetime(2013, 5, 10, 10, 5, 20, 0, timezone.utc),
      lambda time: time == datetime(2014, 12, 5, 7, 13, 0, 0, timezone.utc))

  execs.check()
  
def test_shouldCallRestoreWithAW3CDateAndAUnixTimestamp(fixture):
  inter, execs = fixture.createWithExecutable()

  path = "path/to/file"
  expectedArgs = ("restore", path, "1", "1970-01-01T00:01:33+00:00", 
      "93")
  optionArg = "Foo=Bar"
  time = datetime(1970, 1, 1, 0, 1, 33, tzinfo=timezone.utc)
  options = {"Foo": "Bar"}

  execs.expectMatchingCalls(fixture.lastInterpreterCall(
      lambda args: args[0:5] == expectedArgs and args[5] == "" and 
      args[6] == optionArg, ""))
  inter.restore(path, 1, time, None, options)
  execs.check()

  execs.expectMatchingCalls(fixture.lastInterpreterCall(
      lambda args: args[0:5] == expectedArgs and args[5] == "the-dest" and 
      args[6] == optionArg, ""))
  inter.restore(path, 1, time, "the-dest", options)
  execs.check()

