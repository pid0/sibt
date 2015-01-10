import pytest
import os
from sibt.configuration.exceptions import ConfigConsistencyException
from test.common.execmock import ExecMock
from test.common import execmock
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from test.common.assertutil import iterableContainsInAnyOrder
from sibt.infrastructure.interpreterfuncnotimplementedexception import \
    InterpreterFuncNotImplementedException
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException
from datetime import datetime, timezone
from functools import partial

EpochPlus93Sec = datetime(1970, 1, 1, 0, 1, 33, tzinfo=timezone.utc)
EpochPlus93SecW3C = "1970-01-01T00:01:33+00:00"

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
    self.interpreterPath = str(path)
    os.chmod(str(path), 0o700)

    return self._create(path, name)

  def lastInterpreterCall(self, args, result, options=dict()):
    return (self.interpreterPath, args, result, options)
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
  execs.expect(fixture.interpreterPath, execmock.call(
      lambda args: args[0] == "sync" and set(args[1:3]) == 
          set(["First=foo", "Second=/tmp/quux"]) and len(args) == 3))

  interpreter.sync(options)

  execs.check()

def test_shouldReturnEachNonEmptyLineOfOutputAsAnAvailableOption(fixture):
  interpreter, execs = fixture.createWithExecutable()

  execs.expect(fixture.interpreterPath, execmock.call(
    ("available-options",), ret=["A ", "B", " ", "C"]))

  assert interpreter.availableOptions == ["A", "B", "C"]
  execs.check()

def test_shouldParseUnixTimestampsAndW3CDateTimesAsVersions(fixture):
  inter, execs = fixture.createWithExecutable()
  path = "/etc/config"

  execs.expect(fixture.interpreterPath, execmock.call(
      lambda args: args[0] == "versions-of" and args[1] == "/etc/config" and 
      args[2] == "2" and args[3] == "Blah=quux", ret="""
      250
      2013-05-10T13:05:20+03:00
      2014-12-05T05:13:00-02:00
      """.splitlines()))

  assert iterableContainsInAnyOrder(
      inter.versionsOf(path, 2, {"Blah": "quux"}),
      lambda time: time == datetime(1970, 1, 1, 0, 4, 10, 0, timezone.utc),
      lambda time: time == datetime(2013, 5, 10, 10, 5, 20, 0, timezone.utc),
      lambda time: time == datetime(2014, 12, 5, 7, 13, 0, 0, timezone.utc))

  execs.check()
  
def test_shouldCallRestoreWithAW3CDateAndAUnixTimestamp(fixture):
  inter, execs = fixture.createWithExecutable()

  path = "path/to/file"
  expectedArgs = ("restore", path, "1", EpochPlus93SecW3C, "93")
  time = EpochPlus93Sec

  options = {"Foo": "Bar"}
  optionArg = "Foo=Bar"

  def expectRestoreCall(expectedDestination):
    execs.expect(fixture.interpreterPath, execmock.call(
        lambda args: args[0:5] == expectedArgs and 
        args[5] == expectedDestination and 
        args[6] == optionArg, ""))

  expectRestoreCall("")
  inter.restore(path, 1, time, None, options)
  execs.check()

  expectRestoreCall("the-dest")
  inter.restore(path, 1, time, "the-dest", options)
  execs.check()

def test_shouldReturnIterableOfFilesSplitAtNullWhenAskedForListing(fixture):
  inter, execs = fixture.createWithExecutable()

  files = ["movie  ", "folder/", "text"]
  path = "some/file"
  execs.expect(fixture.interpreterPath, execmock.call(
    ("list-files", path, "2", EpochPlus93SecW3C, "93", "0", "Loc1=/place"), 
    ret=files, delimiter="\0"))

  assert list(inter.listFiles(path, 2, EpochPlus93Sec, False,
      {"Loc1": "/place"})) == files

  execs.check(False)

def test_shouldGatherEachLineOfOutputAsLocationIndicesWhenCallingWritesTo(
    fixture):
  inter, execs = fixture.createWithExecutable()

  execs.expect(fixture.interpreterPath, execmock.call(("writes-to",),
      ret=["1", "2"]))
  assert set(inter.writeLocIndices) == set([1, 2])

  execs.check(True)

def test_shouldThrowNotImplementedExceptionIfExecutableReturns200(fixture):
  def throwExWithExitCode(exitCode, *args):
    raise ExternalFailureException("", [], exitCode)

  def checkExitCodeAndExceptionType(code, expectedExType):
    inter, execs = fixture.createWithExecutable()

    execs.expect(fixture.interpreterPath, execmock.call(
        partial(throwExWithExitCode, code), anyNumber=True))
    with pytest.raises(expectedExType):
      inter.writeLocIndices
    with pytest.raises(expectedExType):
      inter.versionsOf("file", 2, dict())
    with pytest.raises(expectedExType):
      inter.sync(dict())

  checkExitCodeAndExceptionType(200, InterpreterFuncNotImplementedException)
  checkExitCodeAndExceptionType(1, ExternalFailureException)

