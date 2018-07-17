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

import pwd
import os.path
import os

def _sibtSubDir(parentDir):
  return os.path.join(parentDir, "sibt")

class UserBasePaths(object):
  def __init__(self, uid):
    self._uid = uid
    self.readonlyDir = _sibtSubDir("/usr/share")

  @classmethod
  def forCurrentUser(clazz):
    return clazz(os.getuid())

  def isRoot(self):
    return self._uid == 0

  @property
  def varDir(self):
    if self.isRoot():
      return _sibtSubDir("/var/lib")
    else:
      return os.path.join(self.getUserSibtDir(), "var")

  @property
  def configDir(self):
    if self.isRoot():
      return _sibtSubDir("/etc")
    else:
      return os.path.join(self.getUserSibtDir(), "config")

  def getUserSibtDir(self):
    return os.path.join(pwd.getpwuid(self._uid)[5], ".sibt")
