import pytest
from test.sibt.application.intermediateschedulertest import \
    IntermediateSchedulerTestFixture
from sibt.application.outputcapturingscheduler import OutputCapturingScheduler
from test.common.builders import buildScheduling, constantTimeClock, \
    mockSched, anyScheduling, localLocation, execEnvironment
from test.common.bufferingoutput import BufferingOutput
from test.common.rfc3164syslogserver import Rfc3164SyslogServer
from test.common.assertutil import iterToTest, strToTest
from test.common.bufferinglogger import BufferingLogger
from test.sibt.infrastructure.utillinuxsyslogger_test import loggerOptions

TestPort = 6453

class Fixture(IntermediateSchedulerTestFixture):
  def __init__(self, tmpdir):
    self.logFile = tmpdir / "logfile"

  def construct(self, wrappedSched):
    return OutputCapturingScheduler(wrappedSched, constantTimeClock(), 
        BufferingOutput(), False)
  
  def execute(self, wrappedExecuteFunc, scheduling):
    self.scheduler = self.makeSched(subExecute=wrappedExecuteFunc)
    return self.scheduler.execute(execEnvironment(logger=BufferingLogger()), 
        scheduling)

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
  
  def sysloggedScheduling(self, **options):
    return buildScheduling(**options,
        Syslog=True, SyslogOptions=loggerOptions(TestPort))

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldRunTheWrappedSchedsExecuteWithTheNewLogger(fixture):
  returnedObject = object()
  scheduling = fixture.sysloggedScheduling()

  def subExecute(execEnv, passedScheduling):
    assert passedScheduling == scheduling
    execEnv.logger.log("from sub-execute")
    return returnedObject

  assert fixture.executeWithSyslogServer(subExecute, scheduling) is \
      returnedObject
  assert b"from sub-execute" in fixture.singleSyslogPacket.message

def test_shouldLogAnErrorIfAnExecutionFails(fixture):
  def subExecute(*_):
    return False

  scheduling = fixture.sysloggedScheduling(
      LogFile=localLocation(str(fixture.logFile)),
      Stderr=True)

  fixture.executeWithSyslogServer(subExecute, scheduling)
  
  assert b"failed" in fixture.singleSyslogPacket.message
  assert fixture.singleSyslogPacket.severity == "err"

  strToTest(fixture.logFile.read()).shouldInclude(
      scheduling.ruleName, "failed")

def test_shouldLogAnErrorIfAnInternalExceptionOccurs(fixture):
  class TestException(Exception):
    def __str__(self):
      return "abyss"
  def subExecute(*_):
    raise TestException()

  with pytest.raises(TestException):
    fixture.executeWithSyslogServer(subExecute, 
        fixture.sysloggedScheduling())
  
  strToTest(fixture.firstSyslogPacket.message).shouldInclude(
      b"internal", b"exception")
  assert b"abyss" in fixture.allSyslogMessages
  assert fixture.firstSyslogPacket.severity == "err"

def test_shouldLogSuccessesIfAskedTo(fixture):
  assert "LogSuccess" in fixture.optionNames

  def subExecute(*_):
    return True

  scheduling = fixture.sysloggedScheduling(LogSuccess=True)

  fixture.executeWithSyslogServer(subExecute, scheduling)
  
  assert b"success" in fixture.singleSyslogPacket.message
  assert fixture.singleSyslogPacket.severity == "notice"
