import importlib.machinery
from sibt.infrastructure.pymoduleloader import PyModuleLoader

class PyModuleSchedulerLoader(object):
  def __init__(self, containingPackage):
    self.loader = PyModuleLoader(containingPackage)

  def loadFromFile(self, path, moduleName, initArgs):
    ret = self.loader.loadFromFile(path, moduleName)
    ret.name = moduleName
    ret.init(*initArgs)
    return ret

