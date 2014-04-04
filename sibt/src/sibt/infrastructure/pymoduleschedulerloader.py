import importlib.machinery

class PyModuleSchedulerLoader(object):
  def __init__(self, containingPackage):
    self.containingPackage = containingPackage

  def loadFromFile(self, path, moduleName, initArgs):
    fullName = self.containingPackage + "." + moduleName
    loader = importlib.machinery.SourceFileLoader(fullName, path)
    ret = loader.load_module(fullName)
    ret.name = moduleName
    ret.init(*initArgs)
    return ret

