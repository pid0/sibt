import os.path
from sibt.domain.exceptions import LocationInvalidException

class RemoteLocation(object):
  def __init__(self, protocol, login, host, port, path):
    self.protocol = protocol
    self.login = login
    self.host = host
    self.port = port

    if len(host) == 0:
      raise LocationInvalidException(self._strWithPath(path), "has no host")
    if len(path) == 0:
      raise LocationInvalidException(self._strWithPath(path), "has no path")

    self._filePath = FilePath.fromString(path)
    self.path = str(self._filePath)

  def _strWithPath(self, path):
    return "{0}://{1}{2}{3}{4}".format(self.protocol,
        self.login + "@" if self.login != "" else "",
        self.host,
        ":" + self.port if self.port != "" else "",
        path)

  def __str__(self):
    return self._strWithPath(self._filePath)

class LocalLocation(object):
  def __init__(self, absolutePath):
    if not os.path.isabs(absolutePath):
      raise LocationInvalidException(absolutePath, "is not absolute")

    self._initialPath = absolutePath
    self.path = str(FilePath.fromString(absolutePath))
    self.protocol = "file"

  @property
  def existsAsADir(self):
    return os.path.isdir(self._initialPath)
  @property
  def isAFile(self):
    return os.path.isfile(self._initialPath)

  def contains(self, other):
    return self.relativePathTo(other) is not None

  def relativePathTo(self, other):
    resolvedPath = FilePath.fromString(other._initialPath).withLinksResolved
    resolvedContainer = FilePath.fromString(self._initialPath, 
        forceResolveBasename=True).withLinksResolved

    return resolvedContainer.relativePathTo(resolvedPath)

  def __str__(self):
    return self.path
  def __repr__(self):
    return "LocalLocation{0}".format((self._initialPath,))

class FilePath(object):
  @classmethod
  def fromString(clazz, string, forceResolveBasename=False):
    return clazz([component for component in string.split("/") if 
        component != "" and component != "."], 
        forceResolveBasename or string.endswith("/"), 
        string.startswith("/"))

  def __init__(self, components, resolveBasename=False,
      isAbsolute=True):
    self._components = components if components != [] or isAbsolute else ["."]
    self.resolveBasename = resolveBasename
    self.isAbsolute = isAbsolute

  @property
  def parent(self):
    return FilePath(self._components[:-1])

  @property
  def basename(self):
    return self._components[-1]

  def relativePathTo(self, pathWithin):
    if pathWithin._components[:len(self._components)] != self._components:
      return None
    return str(FilePath(pathWithin._components[len(self._components):], 
        isAbsolute=False))

  @property
  def withLinksResolved(self):
    if self.resolveBasename:
      return FilePath.fromString(os.path.realpath(str(self))) 
    else:
      return FilePath.fromString(os.path.realpath(str(self.parent)) + "/" + 
          self.basename)

  def __str__(self):
    return ("/" if self.isAbsolute else "") + "/".join(self._components)

