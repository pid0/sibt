import pytest
import os
from test.common.execmock import ExecMock
from test.common import execmock
from sibt.infrastructure.functionmodulesynchronizer import \
    FunctionModuleSynchronizer
from test.common.assertutil import iterToTest, dictIncludes
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException, \
    ModuleFunctionNotImplementedException
from datetime import datetime, timezone
from test.common import mock
from test.common.builders import remoteLocation, localLocation, location, \
    anyUTCDateTime

EpochPlus93Sec = datetime(1970, 1, 1, 0, 1, 33, tzinfo=timezone.utc)
EpochPlus93SecW3C = "1970-01-01T00:01:33+00:00"

class Fixture(object):
  def __init__(self):
    self.functions = mock.mock()
    self.syncer = FunctionModuleSynchronizer(self.functions, 
        "some-synchronizer")

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldCallAppropriateFunctionForSynchronization(fixture):
  options = {"One": "1", "Two": "two"}

  fixture.functions.expectCalls(mock.callMatching("callVoid",
    lambda funcName, args, usedOptions: funcName == "sync" and
        len(args) == 0 and usedOptions == options))

  fixture.syncer.sync(options)

  fixture.functions.checkExpectedCalls()

def test_shouldWrapFunctionNotImplementedException(fixture):
  def throwNotImplementedEx(*args):
    raise ModuleFunctionNotImplementedException("")

  fixture.functions.expectCalls(mock.callMatching("callVoid", 
    throwNotImplementedEx))

  with pytest.raises(SynchronizerFuncNotImplementedException) as ex:
    fixture.syncer.sync({})
  assert ex.value.synchronizerName == fixture.syncer.name

def test_shouldReturnFuzzyOutputAsAvailableOptions(fixture):
  ret = ["A", "B"]

  fixture.functions.expectCalls(mock.callMatching("callFuzzy",
    lambda funcName, *_: funcName == "available-options", ret=ret))

  assert fixture.syncer.availableOptions == ret

def test_shouldParseUnixTimestampsAndW3CDateTimesAsVersions(fixture):
  path = "/etc/config"

  fixture.functions.expectCalls(mock.callMatching("callFuzzy",
      lambda funcName, args, _: funcName == "versions-of" and 
      args[0] == path and args[1] == "2", ret=[
      "250",
      "2013-05-10T13:05:20+03:00",
      "2014-12-05T05:13:00-02:00"]))

  iterToTest(fixture.syncer.versionsOf(path, 2, {})).shouldContainInAnyOrder(
      datetime(1970, 1, 1, 0, 4, 10, 0, timezone.utc),
      datetime(2013, 5, 10, 10, 5, 20, 0, timezone.utc),
      datetime(2014, 12, 5, 7, 13, 0, 0, timezone.utc))
  
def test_shouldCallRestoreWithAW3CDateAndAUnixTimestamp(fixture):
  path = "path/to/file"
  expectedArgs = [path, "1", EpochPlus93SecW3C, "93", ""]
  time = EpochPlus93Sec

  fixture.functions.expectCalls(mock.callMatching("callVoid", 
    lambda funcName, args, _: funcName == "restore" and 
    list(args) == expectedArgs))

  fixture.syncer.restore(path, 1, time, None, {})

  fixture.functions.checkExpectedCalls()

def test_shouldReturnExactOutputAsFileListing(fixture):
  listing = object()
  path = "some/file"
  expectedOptions = {"Opt": "bar"}

  fixture.functions.expectCalls(mock.callMatching("callExact", 
    lambda funcName, args, options: funcName == "list-files" and list(args) == 
      [path, "2", EpochPlus93SecW3C, "93", "0"], ret=listing))

  assert fixture.syncer.listFiles(path, 2, EpochPlus93Sec, False, 
      expectedOptions) is listing

def test_shouldTreatFirstLineOfPortOutputAsWrittenToFlag(fixture):
  def protocolsCall(number, ret):
    return mock.callMatching("callFuzzy", lambda funcName, args, _:
        funcName == "info-of-port" and args[0] == number, ret=ret)

  fixture.functions.expectCallsInAnyOrder(
    protocolsCall("1", ["1", "a", "b"]),
    protocolsCall("2", ["1", "c"]),
    protocolsCall("3", ["0", "d", "e", "f"]),
    protocolsCall("4", []))

  iterToTest(fixture.syncer.ports).shouldContainMatching(
      lambda port: port.supportedProtocols == ["a", "b"] and port.isWrittenTo,
      lambda port: port.supportedProtocols == ["c"] and port.isWrittenTo,
      lambda port: port.supportedProtocols == ["d", "e", "f"] and \
          not port.isWrittenTo)

def test_shouldConvertArgumentsAndOptionsToStringsDependingOnTheirType(fixture):
  options = {
      "SomePlace": location("/home//foo/"),
      "Loc1": location("/tmp")}

  fixture.functions.expectCalls(mock.callMatching("callVoid",
      lambda _, args, receivedOptions: args[4] == "/media/foo" and
        receivedOptions["SomePlace"] == "/home/foo" and
        receivedOptions["Loc1"] == "/tmp"))

  fixture.syncer.restore("foo", 1, anyUTCDateTime(), 
      location("/media/foo/"), options)

  fixture.functions.checkExpectedCalls()

def test_shouldEncodeLocationsAsMultipleOptions(fixture):
  fixture.functions.expectCalls(mock.callMatching("callVoid",
    lambda _, args, options: dictIncludes(options, {
      "SomePlaceProtocol": "ftp",
      "SomePlaceLogin": "foo",
      "SomePlaceHost": "mansion",
      "SomePlacePort": "10",
      "SomePlacePath": "/blah/quux",

      "LocalProtocol": "file",
      "LocalPath": "/foo",

      "RestoreLogin": "",
      "RestoreHost": "blah",
      "RestorePath": "/foo" })))

  fixture.syncer.restore("file", 2, anyUTCDateTime(),
      remoteLocation("http", host="blah", path="/foo"), 
      { "SomePlace": remoteLocation(protocol="ftp",
        login="foo",
        host="mansion",
        port="10",
        path="/blah/quux"),
        "Local": localLocation("/foo") })

  fixture.functions.checkExpectedCalls()
