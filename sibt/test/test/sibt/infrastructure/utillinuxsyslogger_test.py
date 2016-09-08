import pytest
from sibt.infrastructure.utillinuxsyslogger import UtilLinuxSysLogger
from sibt.infrastructure.exceptions import ExternalFailureException
from test.common.rfc3164syslogserver import Rfc3164SyslogServer
from test.common.assertutil import iterToTest
from test.sibt.infrastructure.linebufferedloggertest import \
    LineBufferedLoggerTest

TestPort = 6732

def loggerOptions(testPort):
  return "--udp --server localhost --port {0} --rfc3164".format(testPort)

class Fixture(object):
  def make(self, port=None, **kwargs):
    return UtilLinuxSysLogger(loggerOptions(port or TestPort), **kwargs)

  def testServer(self):
    return Rfc3164SyslogServer(TestPort)

  def callWithLoggerAndClose(self, func):
    with self.testServer() as self.lineBufferedTestServer:
      logger = self.make()
      func(logger)
      logger.close()

  def readLines(self):
    return [packet.message.decode() for packet in 
        self.lineBufferedTestServer.packets]

@pytest.fixture
def fixture():
  return Fixture()

class Test_UtilLinuxSysLoggerTest(LineBufferedLoggerTest):
  def test_shouldUseTheUtilLinuxLoggerProgramForLogging(self, fixture):
    logger = fixture.make(prefix=b"prefix")

    with fixture.testServer() as server:
      logger.write(b"foo\n")

    iterToTest(server.packets).shouldContainMatching(
        lambda packet: packet.message == b"prefix: foo")
  
  def test_shouldUseTheSpecifiedFacilityAndSeverity(self, fixture):
    logger = fixture.make(facility="mail", severity="warning")

    with fixture.testServer() as server:
      logger.write(b"\n")
      logger.write(b"\n", severity="err")
      logger.write(b"\n", facility="user")

    iterToTest(server.packets).shouldContainMatching(
        lambda packet:
          packet.facility == "mail" and
          packet.severity == "warning",
        lambda packet:
          packet.facility == "mail" and
          packet.severity == "err",
        lambda packet:
          packet.facility == "user" and
          packet.severity == "warning")

  def test_shouldThrowAnExceptionIfTheLoggerProgramFails(self, fixture):
    logger = fixture.make(port=-1)

    with pytest.raises(ExternalFailureException):
      logger.write(b"\n")

  def test_shouldPassTheSpecifiedTag(self, fixture):
    logger = fixture.make(tag="beer")

    with fixture.testServer() as server:
      logger.write(b"\n")

    iterToTest(server.packets).shouldContainMatching(
        lambda packet: packet.tag == b"beer")
