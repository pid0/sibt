import os
from sibt.domain.exceptions import LockException
import fcntl
from contextlib import contextmanager
import errno

@contextmanager
def _mutex(lockFilePath):
  with open(lockFilePath, "wb") as lockFile:
    try:
      fcntl.lockf(lockFile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as ex:
      if ex.errno not in [errno.EAGAIN, errno.EACCES]:
        raise
      raise LockException() from ex

    yield

class FcntlMutexManager(object):
  def __init__(self, lockDir):
    self.lockDir = lockDir
  
  def lockForId(self, lockId):
    return _mutex(os.path.join(self.lockDir, lockId))
