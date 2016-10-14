import pytest
import tempfile
import os

from test.common.assertutil import iterToTest, FakeException
from test.common.builders import mockSyncer, optInfo, port, localLocation, \
    sshLocation, mkSyncerOpts
from test.common import mock
from test.common.execmock import ExecMock
from test.common import execmock
from sibt.infrastructure import types
from sibt.application.sshfsautomountingsynchronizer import \
    SSHFSAutoMountingSynchronizer, isExtensible

class Fixture(object):
  def init(self, ports, availableOptions=[]):
    wrapped = mockSyncer(availableOptions=availableOptions, ports=ports)
    self.wrapped = wrapped
    self.processRunner = LoggingProcessRunner()
    self.syncer = SSHFSAutoMountingSynchronizer(wrapped, self.processRunner)

  def protocolsOfPort(self, portNumber):
    return iterToTest(self.syncer.ports[portNumber - 1].supportedProtocols)

  def call(self, funcName, testOptions, inputOptions):
    returnValue = object()
    args = (object(), object())
    def subFunc(options, *passedArgs):
      assert passedArgs == args
      testOptions(options)
      return returnValue

    setattr(self.wrapped, funcName, subFunc)
    func = getattr(self.syncer, funcName)
    assert func(mkSyncerOpts(**inputOptions), *args) == returnValue

@pytest.fixture
def fixture():
  return Fixture()

class LoggingProcessRunner(object):
  def __init__(self):
    self.executions = []

  def execute(self, *args, **kwargs):
    self.executions.append(args)

ThreeFilePorts = [port(["file"]), port(["file"]), port(["file"])]
TwoFilePorts = [port(["file"]), port(["file"]), port(["file"])]

def test_shouldAddRemoteShellCommandOptionAndSSHProtocolToEachPort(fixture):
  option = object()
  fixture.init(availableOptions=[option], ports=[
    port(["file", "ftp"]), port(["file"])])

  assert fixture.syncer.availableOptions == [option, 
    optInfo("RemoteShellCommand", types.String)]

  fixture.protocolsOfPort(1).shouldContainInAnyOrder("file", "ftp", "ssh")
  fixture.protocolsOfPort(2).shouldContainInAnyOrder("file", "ssh")

def test_shouldNotAllowSyncersThatAlreadySupportSSHInAnyWay():
  assert not isExtensible(mockSyncer(ports=[
    port(["file", "ssh"]), port(["file"])]))
  assert not isExtensible(mockSyncer(ports=[
    port(["file"]), port(["file", "ssh"])]))

def test_shouldNotAllowSyncersThatDontSupportLocalFiles():
  assert not isExtensible(mockSyncer(ports=[port(["file"]), port(["ftp"])]))

def test_shouldReplaceAutomountedLocOptionsByTheLocalMountPoints(fixture):
  inputOptions = dict(
      Loc1=sshLocation(path="/foo"),
      Loc2=localLocation(path="/bar"),
      Loc3=sshLocation(path="/quux"))
  outputOptions = dict()

  def testOptions(options):
    outputOptions.update(options)

  fixture.init(ThreeFilePorts)
  fixture.call("versionsOf", testOptions, inputOptions)

  assert outputOptions["Loc1"].protocol == "file"
  assert outputOptions["Loc1"].path.startswith(tempfile.gettempdir())
  assert outputOptions["Loc2"].path == "/bar"
  assert outputOptions["Loc3"].path != "/quux"

def test_shouldUnmountAndCleanUpMountDirsEvenIfAnExceptionIsThrown(fixture):
  options = dict(Loc1=sshLocation(path="/foo"), Loc2=sshLocation(path="/bar"))
  fixture.init(TwoFilePorts)

  newLocPaths = []
  def subSync(newOptions):
    assert all(os.path.isdir(loc.path) for loc in newOptions.locs)
    newLocPaths.extend([loc.path for loc in newOptions.locs])
    raise FakeException()

  with pytest.raises(FakeException):
    fixture.call("sync", subSync, options)

  for locPath in newLocPaths:
    assert not os.path.lexists(locPath)
