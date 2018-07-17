# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from test.sibt.application.intermediateschedulertest import \
    IntermediateSchedulerTestFixture
from sibt.application.loggingscheduler import LoggingScheduler
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
    return LoggingScheduler(wrappedSched, constantTimeClock(), 
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
    return buildScheduling(Syslog=True, SyslogOptions=loggerOptions(TestPort), 
        **options)

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
