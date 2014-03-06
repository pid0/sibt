class Paths(object):
  def __init__(self, basePaths):
    self.basePaths = basePaths

  def rulesDir(self):
    return self.basePaths.configDir + "/rules"
  def interpretersDir(self):
    return self.basePaths.configDir + "/interpreters"
  def schedulersDir(self):
    return self.basePaths.configDir + "/schedulers"

  def varDir(self):
    return self.basePaths.varDir
  def configDir(self):
    return self.basePaths.configDir

  rulesDir = property(rulesDir)
  interpretersDir = property(interpretersDir)
  schedulersDir = property(schedulersDir)
  varDir = property(varDir)
  configDir = property(configDir)
