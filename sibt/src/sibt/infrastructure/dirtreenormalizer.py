import os.path
import os

class DirTreeNormalizer(object):
  def __init__(self, paths):
    self.paths = paths

  def _createIfDoesntExist(self, path):
    if not os.path.isdir(path):
      os.makedirs(path)

  def createNotExistingDirs(self):
    for path in [self.paths.rulesDir,
        self.paths.synchronizersDir,
        self.paths.schedulersDir,
        self.paths.enabledDir,
        self.paths.varDir]:
      self._createIfDoesntExist(path)

