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
