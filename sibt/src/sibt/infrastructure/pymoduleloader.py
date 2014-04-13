import importlib.machinery

class PyModuleLoader(object):
  def __init__(self, containingPackage):
    self.containingPackage = containingPackage

  def loadFromFile(self, path, moduleName):
    fullName = self.containingPackage + "." + moduleName
    loader = importlib.machinery.SourceFileLoader(fullName, path)
    return loader.load_module(fullName)
