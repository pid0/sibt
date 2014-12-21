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
  def interpretersDir(self):
    return os.path.join(self.configDir, "interpreters")
  @property
  def schedulersDir(self):
    return os.path.join(self.configDir, "schedulers")
  @property
  def enabledDir(self):
    return os.path.join(self.configDir, "enabled")
  @property
  def readonlySchedulersDir(self):
    return os.path.join(self.readonlyDir, "schedulers")
  @property
  def readonlyInterpretersDir(self):
    return os.path.join(self.readonlyDir, "interpreters")
  @property
  def runnersDir(self):
    return os.path.join(self.readonlyDir, "runners")

