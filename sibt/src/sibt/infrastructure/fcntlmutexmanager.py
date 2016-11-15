import os
from sibt.domain.exceptions import LockException
import fcntl
from contextlib import contextmanager
import errno

def writeLock(lockFile):
  _lock(lockFile, fcntl.LOCK_EX)
def readLock(lockFile):
  _lock(lockFile, fcntl.LOCK_SH)

def _lock(lockFile, lockType):
  fcntl.lockf(lockFile, lockType | fcntl.LOCK_NB)

def tryToLock(lockFile, lockFunc):
  try:
    lockFunc(lockFile)
    return True
  except OSError as ex:
    if ex.errno not in [errno.EAGAIN, errno.EACCES]:
      raise
    return False

@contextmanager
def _mutex(lockFilePath):
  with open(lockFilePath, "wb") as lockFile:
    if not tryToLock(lockFile, writeLock):
      raise LockException()
    yield

class FcntlMutexManager(object):
  def __init__(self, lockDir):
    self.lockDir = lockDir
  
  def lockForId(self, lockId):
    return _mutex(os.path.join(self.lockDir, lockId))
