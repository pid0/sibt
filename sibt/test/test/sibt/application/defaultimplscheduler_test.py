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

from test.common.builders import anyScheduling, mockSched, execEnvironment
from sibt.application.defaultimplscheduler import DefaultImplScheduler
from test.common import mock

def test_shouldCallRunSynchronizerWhenExecutedAsADefault():
  returnedObject = object()
  execEnv = mock.mock()
  execEnv.expectCalls(mock.call("runSynchronizer", (), ret=returnedObject))

  schedWithoutExecute = object()
  scheduler = DefaultImplScheduler(schedWithoutExecute)

  assert scheduler.execute(execEnv, anyScheduling()) is returnedObject

def test_shouldCallTheWrappedSchedsExecuteMethodIfItHasOne():
  wrappedSched = mock.mock()
  execEnv, scheduling, returnedObject = object(), object(), object()

  wrappedSched.expectCalls(mock.call("execute", (execEnv, scheduling), 
    ret=returnedObject))

  assert DefaultImplScheduler(wrappedSched).execute(execEnv, scheduling) is \
      returnedObject
