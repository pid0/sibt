import os.path
from sibt.domain.exceptions import LocationInvalidException

class LocalLocation(object):
  def __init__(self, absolutePath):
    if not os.path.isabs(absolutePath):
      raise LocationInvalidException(absolutePath, "is not absolute")

    self._initialPath = absolutePath
    self.path = self._normalize(absolutePath)

  def _normalize(self, path):
    return "/" + "/".join(component for component in path.split("/") if 
        len(component) > 0 and component != ".")

  @property
  def existsAsADir(self):
    return os.path.isdir(self._initialPath)
  @property
  def isAFile(self):
    return os.path.isfile(self._initialPath)


  def __str__(self):
    return self.path
  def __repr__(self):
    return "LocalLocation{0}".format((self._initialPath,))
