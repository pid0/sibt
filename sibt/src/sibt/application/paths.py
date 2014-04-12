import os.path

class Paths(object):
  def __init__(self, basePaths):
    self.varDir = basePaths.varDir
    self.readonlyDir = basePaths.readonlyDir
    self.configDir = basePaths.configDir

  def rulesDir(self):
    return os.path.join(self.configDir, "rules")
  def interpretersDir(self):
    return os.path.join(self.configDir, "interpreters")
  def schedulersDir(self):
    return os.path.join(self.configDir, "schedulers")
  def enabledDir(self):
    return os.path.join(self.configDir, "enabled")
  def readonlySchedulersDir(self):
    return os.path.join(self.readonlyDir, "schedulers")
  def readonlyInterpretersDir(self):
    return os.path.join(self.readonlyDir, "interpreters")
  def runnersDir(self):
    return os.path.join(self.readonlyDir, "runners")

  rulesDir = property(rulesDir)
  interpretersDir = property(interpretersDir)
  schedulersDir = property(schedulersDir)
  enabledDir = property(enabledDir)
  readonlySchedulersDir = property(readonlySchedulersDir)
  readonlyInterpretersDir = property(readonlyInterpretersDir)
  runnersDir = property(runnersDir)

