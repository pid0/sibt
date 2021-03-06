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
from sibt.infrastructure.filelogger import FileLogger
from datetime import datetime, timezone
from test.common.builders import anyUTCDateTime, constantTimeClock
from test.common.presetcyclingclock import PresetCyclingClock
from test.sibt.infrastructure.linebufferedloggertest import \
    LineBufferedLoggerTest

class Fixture(object):
  def __init__(self, tmpdir):
    self.logFile = tmpdir / "file"

  def make(self, clock=constantTimeClock(), prefix=""):
    return FileLogger(str(self.logFile), clock, prefix)

  def callWithLoggerAndClose(self, func):
    logger = self.make()
    func(logger)
    logger.close()

  def readLines(self):
    return [line[line.index("]")+2:] for line in 
        self.logFile.read().splitlines()]

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_FileLoggerTest(LineBufferedLoggerTest):
  def test_shouldPrefixAllLinesWithTheCurrentTimeAndAnIdentifier(self, fixture):
    clock = PresetCyclingClock(
        datetime(2000, 3, 4, 21, 20, 0, 0),
        datetime(2001, 4, 3, 22, 0, 5, 0))

    logger = fixture.make(clock, "prefix")
    logger.write(b"foo bar\nbaz quux\n")
    logger.close()

    assert fixture.logFile.read() == \
        "[2000-03-04 21:20:00, prefix] foo bar\n" + \
        "[2001-04-03 22:00:05, prefix] baz quux\n"

  def test_shouldAppendToTheFile(self, fixture):
    previousContent = "previous\n"

    fixture.logFile.write(previousContent)

    logger = fixture.make()
    logger.write(b"foo\n")
    logger.close()

    assert fixture.logFile.read().startswith(previousContent)

  def test_shouldFinishLastLineWhenClosing(self, fixture):
    logger = fixture.make()

    logger.write(b"foo")
    logger.close()

    assert fixture.logFile.read().endswith("foo\n")
