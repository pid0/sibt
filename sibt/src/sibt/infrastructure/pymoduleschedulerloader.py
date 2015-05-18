import importlib.machinery
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from sibt.infrastructure.optioninfoparsingscheduler import \
    OptionInfoParsingScheduler

class PyModuleSchedulerLoader(object):
  def __init__(self, moduleLoader):
    self.loader = moduleLoader

  def loadFromFile(self, path, moduleName, initArgs):
    ret = self.loader.loadFromFile(path, moduleName)
    ret.name = moduleName
    ret.init(*initArgs)
    return OptionInfoParsingScheduler(ret)

