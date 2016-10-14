import pytest
import os
from test.common.execmock import ExecMock
from test.common import execmock
from sibt.infrastructure.functionmodulesynchronizer import \
    FunctionModuleSynchronizer
from test.common.assertutil import iterToTest, dictIncludes, strToTest
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException, \
    ModuleFunctionNotImplementedException
from datetime import datetime, timezone, timedelta
from test.common import mock
from test.common.builders import remoteLocation, localLocation, location, \
    anyUTCDateTime, mkSyncerOpts, toTimestamp
from sibt.infrastructure import types

EpochPlus93Point46Sec = datetime(1970, 1, 1, 0, 1, 33, 460000, timezone.utc)

class Fixture(object):
  def __init__(self):
    self.functions = mock.mock()
    self.syncer = FunctionModuleSynchronizer(self.functions, 
        "some-synchronizer")

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldCallAppropriateFunctionForSynchronization(fixture):
  options = mkSyncerOpts(One="1", Two="two")

  fixture.functions.expectCalls(mock.callMatching("callVoid",
    lambda funcName, args, usedOptions: funcName == "sync" and
        len(args) == 0 and usedOptions == dict(options)))

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

def test_shouldSplitFuzzyOutputForTypeAndNameOfAvailableOptions(fixture):
  ret = ["Default", "b B"]

  fixture.functions.expectCalls(mock.callMatching("callFuzzy",
    lambda funcName, *_: funcName == "available-options", ret=ret))

  assert iterToTest(fixture.syncer.availableOptions).shouldContainMatching(
      lambda opt: opt.name == "Default" and opt.optionType == types.String,
      lambda opt: opt.name == "B" and opt.optionType == types.Bool)

def test_shouldParseUnixTimestampsWithAndWithoutMillisecondsAsVersions(fixture):
  path = "/etc/config"

  fixture.functions.expectCalls(mock.callMatching("callFuzzy",
      lambda funcName, args, _: funcName == "versions-of" and 
      args[0] == path and args[1] == "2", ret=[
      "250",
      "0,999",
      toTimestamp("2013-05-10T13:05:20") + ",025"]))

  iterToTest(fixture.syncer.versionsOf({}, path, 2)).shouldContainInAnyOrder(
      datetime(1970, 1, 1, 0, 4, 10, 0, timezone.utc),
      datetime(1970, 1, 1, 0, 0, 0, 999000, timezone.utc),
      datetime(2013, 5, 10, 13, 5, 20, 25000, timezone.utc))

def test_shouldThrowAnExceptionIfTimestampsAreNotInACorrectFormat(fixture):
  def shouldThrow(timestamp):
    fixture.functions.expectCalls(mock.callMatching("callFuzzy", 
      lambda *_: True, ret=[timestamp]))
    with pytest.raises(ValueError) as ex:
      fixture.syncer.versionsOf({}, "foo", 1)
    strToTest(str(ex)).shouldInclude("timestamp", "format")

  shouldThrow("2,3,")
  shouldThrow("0,1000")
  
def test_shouldCallRestoreWithAUnixTimestampWithMilliseconds(fixture):
  path = "path/to/file"
  expectedArgs = [path, "1", "93,460", ""]
  time = EpochPlus93Point46Sec

  fixture.functions.expectCalls(mock.callMatching("callVoid", 
    lambda funcName, args, _: funcName == "restore" and 
    list(args) == expectedArgs))

  fixture.syncer.restore({}, path, 1, time, None)

  fixture.functions.checkExpectedCalls()

def test_shouldEvaluateExactOutputAndCallTheClientWhenListingFiles(fixture):
  listing = ["foo", "bar"]
  visitedFiles = []
  def visitor(fileName):
    visitedFiles.append(fileName)

  path = "some/file"
  expectedOptions = {"Opt": "bar"}

  fixture.functions.expectCalls(mock.callMatching("callExact", 
    lambda funcName, args, options: funcName == "list-files" and list(args) == 
      [path, "2", "93,460", "0"], ret=listing))

  fixture.syncer.listFiles(expectedOptions, visitor, path, 2, 
      EpochPlus93Point46Sec, False)
  assert visitedFiles == listing

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
  enum = types.Enum("A", "B")
  options = {
      "SomePlace": location("/home//foo/"),
      "Loc1": location("/tmp"),
      "Yes": True,
      "No": False,
      "Number": 934,
      "Interval": timedelta(minutes=2, seconds=3.5),
      "Choice": enum.A}

  fixture.functions.expectCalls(mock.callMatching("callVoid",
      lambda _, args, receivedOptions: args[3] == "/media/foo" and
        receivedOptions["SomePlace"] == "/home/foo" and
        receivedOptions["Loc1"] == "/tmp" and
        receivedOptions["Yes"] == "1" and 
        receivedOptions["No"] == "0" and 
        receivedOptions["Number"] == "934" and 
        receivedOptions["Interval"] == "123" and 
        receivedOptions["Choice"] == "A"))

  fixture.syncer.restore(options, "foo", 1, anyUTCDateTime(), 
      location("/media/foo/"))

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

  options = { 
      "SomePlace": remoteLocation(
        protocol="ftp", 
        login="foo", 
        host="mansion", 
        port="10", 
        path="/blah/quux"), 
      "Local": localLocation("/foo") }

  fixture.syncer.restore(options, "file", 2, anyUTCDateTime(),
      remoteLocation("http", host="blah", path="/foo"))

  fixture.functions.checkExpectedCalls()
