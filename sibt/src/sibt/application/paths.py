import os.path

class Paths(object):
  def __init__(self, basePaths):
    self.varDir = basePaths.varDir
    self.readonlyDir = basePaths.readonlyDir
    self.configDir = basePaths.configDir

  @property
  def rulesDir(self):
    return os.path.join(self.configDir, "rules")
  @property
  def synchronizersDir(self):
    return os.path.join(self.configDir, "synchronizers")
  @property
  def schedulersDir(self):
    return os.path.join(self.configDir, "schedulers")
  @property
  def enabledDir(self):
    return os.path.join(self.configDir, "enabled")
  @property
  def logDir(self):
    return os.path.join(self.varDir, "log")
  @property
  def lockDir(self):
    return os.path.join(self.varDir, "locks")
  @property
  def readonlySchedulersDir(self):
    return os.path.join(self.readonlyDir, "schedulers")
  @property
  def readonlySynchronizersDir(self):
    return os.path.join(self.readonlyDir, "synchronizers")
  @property
  def readonlyIncludesDir(self):
    return os.path.join(self.readonlyDir, "include")
  @property
  def runnersDir(self):
    return os.path.join(self.readonlyDir, "runners")

