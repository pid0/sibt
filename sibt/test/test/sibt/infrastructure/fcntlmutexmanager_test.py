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
import sys
from contextlib import contextmanager
import time
from sibt.infrastructure.fcntlmutexmanager import FcntlMutexManager
from sibt.domain.exceptions import LockException
from test.common.interprocesstestfixture import InterProcessTestFixture

class Fixture(InterProcessTestFixture):
  def __init__(self, tmpDirPath):
    super().__init__(
        "test.sibt.infrastructure.fcntlmutexmanager_test",
        tmpDirPath, ["os", "signal", "time"])
    self.tmpDirPath = tmpDirPath
    self.manager = self.makeManager()
  
  def makeManager(self):
    return FcntlMutexManager(self.tmpDirPath)

  @contextmanager
  def lockInAnotherProcess(self, lockId, codeInBody, codeAtTheEnd="pass"):
    code = r"""
      try:
        mutex = fixture.manager.lockForId({0})
        with mutex:
          {1}
      finally:
        {2}""".format(repr(lockId), codeInBody, codeAtTheEnd)

    with self.startInNewProcess(code) as process:
      time.sleep(0.3)
      try:
        yield process
      finally:
        process.kill()

@pytest.fixture
def fixture(tmpdir):
  return Fixture(str(tmpdir))

def test_shouldHaveNoFurtherEffectIfLockCanBeAcquired(fixture):
  with fixture.manager.lockForId("foo"):
    with fixture.manager.lockForId("bar"):
      pass
  with fixture.manager.lockForId("foo"):
    pass

def test_shouldThrowExceptionIfLockIsAlreadyAcquiredByAnotherProcess(fixture):
  with fixture.lockInAnotherProcess("foo", "time.sleep(3)"):
    with pytest.raises(LockException):
      with fixture.manager.lockForId("foo"):
        pass

def test_shouldNotKeepPersistentLocksAround(fixture):
  with fixture.lockInAnotherProcess("foo", 
      "os.kill(os.getpid(), signal.SIGKILL)") as process:
    process.wait()

  with fixture.manager.lockForId("foo"):
    pass

  with fixture.lockInAnotherProcess("foo", 
      "raise Exception()", codeAtTheEnd="time.sleep(3)"):
    with fixture.manager.lockForId("foo"):
      pass
