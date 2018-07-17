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

from test.common import mock
from sibt.infrastructure.teelogger import TeeLogger

def test_shouldImmediatelyWriteAnyChunkToAllOfItsSubLoggers():
  chunk = b"abcdef"

  subLogger1 = mock.mock()
  subLogger2 = mock.mock()

  subLogger1.expectCalls(mock.call("write", (chunk,)))
  subLogger2.expectCalls(mock.call("write", (chunk,)))

  logger = TeeLogger(subLogger1, subLogger2)

  logger.write(chunk)

  subLogger1.checkExpectedCalls()
  subLogger2.checkExpectedCalls()

def test_shouldCloseAllSubLoggersWhenItIsClosed():
  subLogger1 = mock.mock()
  subLogger2 = mock.mock()

  subLogger1.expectCalls(mock.call("close", ()))
  subLogger2.expectCalls(mock.call("close", ()))

  with TeeLogger(subLogger1, subLogger2):
    pass

  subLogger1.checkExpectedCalls()
  subLogger2.checkExpectedCalls()

def test_shouldNotCloseUnclosableSubLoggers():
  subLogger = object()

  TeeLogger(subLogger).close()

def test_shouldPassOnAnyGivenKeywordArgsToWriteFuncs():
  subLogger = mock.mock()

  subLogger.expectCalls(mock.callMatching("write", 
    lambda *args, **kwargs: kwargs == dict(Foo="Bar")))

  TeeLogger(subLogger).write(b"", Foo="Bar")

  subLogger.checkExpectedCalls()
