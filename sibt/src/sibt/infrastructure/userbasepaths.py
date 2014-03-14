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

  def getVarDir(self):
    if self.isRoot():
      return "/var"
    else:
      return self.getUserSibtDir() + "/var"
  def getConfigDir(self):
    if self.isRoot():
      return "/etc"
    else:
      return self.getUserSibtDir() + "/config"

  varDir = property(getVarDir)
  configDir = property(getConfigDir)

  def getUserSibtDir(self):
    return pwd.getpwuid(self._uid)[5] + "/.sibt"
