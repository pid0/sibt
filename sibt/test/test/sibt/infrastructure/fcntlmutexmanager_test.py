import pytest
import sys
import subprocess
from contextlib import contextmanager
import time
from sibt.infrastructure.fcntlmutexmanager import FcntlMutexManager
from sibt.domain.exceptions import LockException
import textwrap

class Fixture(object):
  def __init__(self, tmpDirPath):
    self.tmpDirPath = tmpDirPath
    self.manager = self.makeManager()
  
  def makeManager(self):
    return FcntlMutexManager(self.tmpDirPath)

  @contextmanager
  def lockInAnotherProcess(self, lockId, codeInBody, codeAtTheEnd="pass"):
    code = r"""
      import sys, os, signal, time
      from test.sibt.infrastructure.fcntlmutexmanager_test import Fixture

      try:
        mutex = Fixture(sys.argv[1]).manager.lockForId({0})
        with mutex:
          {1}
      finally:
        {2}""".format(repr(lockId), codeInBody, codeAtTheEnd)

    with subprocess.Popen([sys.executable, "-c", textwrap.dedent(code),
      self.tmpDirPath]) as process:
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
