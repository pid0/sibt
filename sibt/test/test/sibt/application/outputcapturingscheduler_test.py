import pytest
from sibt.application.outputcapturingscheduler import OutputCapturingScheduler
from test.common import mock
from test.common.builders import buildScheduling, constantTimeClock, \
    mockSched, anyScheduling, localLocation
from test.common.bufferingoutput import BufferingOutput
from test.common.rfc3164syslogserver import Rfc3164SyslogServer
from test.common.assertutil import iterToTest, strToTest
from test.sibt.infrastructure.utillinuxsyslogger_test import loggerOptions

TestPort = 6453

class NullLogger(object):
  def write(*args, **kwargs):
    pass
  def close():
    pass

class Fixture(object):
  def __init__(self, tmpdir):
    wrapped = mockSched()
    self.scheduler = OutputCapturingScheduler(wrapped, constantTimeClock(),
        BufferingOutput())

    self.logFile = tmpdir / "logfile"

  def execute(self, runSibtSyncUncontrolled, scheduling):
    subLogger = NullLogger()

    return self.scheduler.execute(scheduling, subLogger, 
        runSibtSyncUncontrolled)

  def executeWithSyslogServer(self, *args):
    with Rfc3164SyslogServer(TestPort) as self.syslogServer:
      return self.execute(*args)

  @property
  def firstSyslogPacket(self):
    return self.syslogServer.packets[0]
  @property
  def singleSyslogPacket(self):
    assert len(self.syslogServer.packets) == 1
    return self.firstSyslogPacket
  @property
  def allSyslogMessages(self):
    return b"".join(packet.message for packet in self.syslogServer.packets)
  
  @property
  def optionNames(self):
    return [optInfo.name for optInfo in self.scheduler.availableOptions]

  def sysloggedScheduling(self, **options):
    return buildScheduling(**options,
        Syslog=True, SyslogOptions=loggerOptions(TestPort))

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldRunSibtSyncUncontrolledWhenExecuted(fixture):
  returnedObject = object()
  def run(logger):
    return returnedObject

  assert fixture.execute(run, anyScheduling()) is returnedObject

def test_shouldLogAnErrorIfAnExecutionFails(fixture):
  def syncUncontrolled(_):
    return False

  scheduling = fixture.sysloggedScheduling(
      LogFile=localLocation(str(fixture.logFile)))

  fixture.executeWithSyslogServer(syncUncontrolled, scheduling)
  
  assert b"failed" in fixture.singleSyslogPacket.message
  assert fixture.singleSyslogPacket.severity == "err"

  strToTest(fixture.logFile.read()).shouldInclude(
      scheduling.ruleName, "failed")

def test_shouldLogAnErrorIfAnInternalExceptionOccurs(fixture):
  class TestException(Exception):
    def __str__(self):
      return "abyss"
  def syncUncontrolled(_):
    raise TestException()

  with pytest.raises(TestException):
    fixture.executeWithSyslogServer(syncUncontrolled, 
        fixture.sysloggedScheduling())
  
  strToTest(fixture.firstSyslogPacket.message).shouldInclude(
      b"internal", b"exception")
  assert b"abyss" in fixture.allSyslogMessages
  assert fixture.firstSyslogPacket.severity == "err"

def test_shouldLogSuccessesIfAskedTo(fixture):
  assert "LogSuccess" in fixture.optionNames

  def syncUncontrolled(_):
    return True

  scheduling = fixture.sysloggedScheduling(LogSuccess=True)

  fixture.executeWithSyslogServer(syncUncontrolled, scheduling)
  
  assert b"success" in fixture.singleSyslogPacket.message
  assert fixture.singleSyslogPacket.severity == "notice"
