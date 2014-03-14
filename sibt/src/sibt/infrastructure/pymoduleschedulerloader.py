import importlib.machinery

class PyModuleSchedulerLoader(object):
  def __init__(self, containingPackage):
    self.containingPackage = containingPackage

  def loadFromFile(self, path, fileName, initArgs):
    moduleName = self.containingPackage + "." + fileName
    loader = importlib.machinery.SourceFileLoader(moduleName, path)
    ret = loader.load_module(moduleName)
    ret.name = fileName[0:-3] if fileName.endswith(".py") else fileName
    ret.init(*initArgs)
    return ret

