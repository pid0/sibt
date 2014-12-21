import pwd
import os.path
import os

class UserBasePaths(object):
  def __init__(self, uid):
    self._uid = uid
    self.readonlyDir = "/usr/share"

  @classmethod
  def forCurrentUser(clazz):
    return clazz(os.getuid())

  def isRoot(self):
    return self._uid == 0

  @property
  def varDir(self):
    if self.isRoot():
      return "/var"
    else:
      return os.path.join(self.getUserSibtDir(), "var")

  @property
  def configDir(self):
    if self.isRoot():
      return "/etc"
    else:
      return os.path.join(self.getUserSibtDir(), "config")

  def getUserSibtDir(self):
    return os.path.join(pwd.getpwuid(self._uid)[5], ".sibt")
