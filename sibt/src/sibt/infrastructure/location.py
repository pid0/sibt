import os.path
from sibt.domain.exceptions import LocationInvalidException, \
    LocationNotAbsoluteException

def _equivalenceClassOf(classes, protocol):
  foundClasses = [clazz for clazz in classes if protocol in clazz]
  if len(foundClasses) == 0:
    return [protocol]
  return foundClasses[0]

_EquivalenceClassesIfRelative = [
    ["scp", "ssh"]]
_EquivalenceClassesIfAbsolute = [
    ["scp", "ssh", "ftp"]]

class RemoteLocation(object):
  def __init__(self, protocol, login, host, port, path):
    self.protocol = protocol
    self.login = login
    self.host = host
    self.port = port
    self._filePath = FilePath.fromString(path)

    if len(path) == 0:
      raise LocationInvalidException(str(self), "has no path")
    if len(host) == 0:
      raise LocationInvalidException(str(self), "has no host")

    self.path = str(self._filePath)

  @property
  def existsAsADir(self):
    return True
  @property
  def isAFile(self):
    return False
  @property
  def isEmpty(self):
    return False

  def contains(self, other):
    return self.relativePathTo(other) is not None

  def relativePathTo(self, other):
    if isinstance(other, LocalLocation):
      return None

    ret = self._filePath.relativePathTo(other._filePath)
    if ret is None:
      return None

    equivClasses = _EquivalenceClassesIfAbsolute if \
        self._filePath.isAbsolute else _EquivalenceClassesIfRelative

    protocolsEqual = self.protocol == other.protocol or \
        self.protocol in _equivalenceClassOf(equivClasses, other.protocol)

    if not protocolsEqual or \
        self.host != other.host:
      return None

    if not self._filePath.isAbsolute and (
        self.login != other.login or
        self.port != other.port):
      return None

    return ret

  def __str__(self):
    return "{0}://{1}{2}{3}{4}".format(self.protocol,
        self.login + "@" if self.login != "" else "",
        self.host,
        ":" + self.port if self.port != "" else "",
        self._filePath if self._filePath.isAbsolute else \
            ("/~/" + str(self._filePath)))
  def __repr__(self):
    return "RemoteLocation{0}".format((self.protocol,
      self.login, self.host, self.port, self.path))
  @property
  def _constituentFields(self):
    return (self.path, self.protocol, self.login, self.host, self.port)
  def __eq__(self, other):
    return self._constituentFields == other._constituentFields
  def __hash__(self):
    return hash(self._constituentFields)

class LocalLocation(object):
  def __init__(self, absolutePath):
    if not os.path.isabs(absolutePath):
      raise LocationNotAbsoluteException(absolutePath)

    self._initialPath = absolutePath
    self.path = str(FilePath.fromString(absolutePath))
    self.protocol = "file"

  @property
  def existsAsADir(self):
    return os.path.isdir(self._initialPath)
  @property
  def isAFile(self):
    return os.path.isfile(self._initialPath)
  @property
  def isEmpty(self):
    return len(os.listdir(self._initialPath)) == 0

  def contains(self, other):
    return self.relativePathTo(other) is not None

  def relativePathTo(self, other):
    if isinstance(other, RemoteLocation):
      return None

    resolvedPath = FilePath.fromString(other._initialPath).withLinksResolved
    resolvedContainer = FilePath.fromString(self._initialPath, 
        forceResolveBasename=True).withLinksResolved

    return resolvedContainer.relativePathTo(resolvedPath)

  def __str__(self):
    return self.path
  def __repr__(self):
    return "LocalLocation({0})".format(repr(self._initialPath))
  def __eq__(self, other):
    return self.path == other.path
  def __hash__(self):
    return hash(self.path)

class FilePath(object):
  @classmethod
  def fromString(clazz, string, forceResolveBasename=False):
    return clazz([component for component in string.split("/") if 
        component != "" and component != "."], 
        forceResolveBasename or string.endswith("/"), 
        string.startswith("/"))

  def __init__(self, components, resolveBasename=False,
      isAbsolute=True):
    self._components = components
    self.resolveBasename = resolveBasename
    self.isAbsolute = isAbsolute

  @property
  def parent(self):
    return FilePath(self._components[:-1])

  @property
  def basename(self):
    return self._components[-1]

  def relativePathTo(self, pathWithin):
    if pathWithin._components[:len(self._components)] != self._components or \
        self.isAbsolute != pathWithin.isAbsolute:
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
    if len(self._components) == 0 and not self.isAbsolute:
      return "."
    return ("/" if self.isAbsolute else "") + "/".join(self._components)
  def __repr__(self):
    return "FilePath{0}".format((self._components,
      self.resolveBasename, self.isAbsolute))
