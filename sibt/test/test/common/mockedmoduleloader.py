class MockedModuleLoader(object):
  def __init__(self, namesToModules):
    self.namesToModules = namesToModules

  def loadFromFile(self, path, name):
    return self.namesToModules[name]

