class ConfigObjectBuilder(object):
  testCounter = 0

  def __init__(self, paths, sysPaths, foldersWriter, name, kwParams):
    self.paths = paths
    self.sysPaths = sysPaths
    self.name = name
    self.kwParams = kwParams
    self.foldersWriter = foldersWriter

  def _withParams(self, **kwargs):
    newParams = dict(self.kwParams)
    for key in kwargs:
      newParams[key] = kwargs[key]
    return self.newBasic(self.paths, self.sysPaths, self.foldersWriter, 
        self.name, newParams)

  def withContent(self, newContent):
    return self._withParams(content=newContent)

  def withAnyName(self):
    ConfigObjectBuilder.testCounter += 1
    return self.withName("any-" + str(ConfigObjectBuilder.testCounter))

  def withName(self, newName):
    return self.newBasic(self.paths, self.sysPaths, self.foldersWriter, 
        newName, dict(self.kwParams))

  def asSysConfig(self, isSysConfig=True):
    return self._withParams(isSysConfig=isSysConfig)

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    pass

  @property
  def content(self):
    return self.kwParams["content"]
  @property
  def configuredPaths(self):
    isSysConfig = self.kwParams.get("isSysConfig", False)
    if isSysConfig:
      return self.sysPaths
    else:
      return self.paths
