from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local

RuleFormat = """
    [Interpreter]
    Name = {syncer}
    Loc1={loc1}
    Loc2={loc2}
    {syncerOpts}

    [Scheduler]
    Name={sched}
    {schedOpts}
"""

def iniFileFormatted(keysToValues):
  return "\n".join(key + "=" + value for key, value in keysToValues.items())


class RuleBuilder(ConfigObjectBuilder):
  def __init__(self, paths, sysPaths, foldersWriter, name, kwParams):
    super().__init__(paths, sysPaths, foldersWriter, name, kwParams)

  def _validLoc(self):
    folder = self.foldersWriter.makeUniqueFolder()
    (folder / "file").write("")
    return str(folder)

  def withSynchronizer(self, syncer):
    return self._withParams(synchronizerName=syncer.name)
  def withScheduler(self, sched):
    return self._withParams(schedulerName=sched.name)
  def withSynchronizerName(self, syncerName):
    return self._withParams(synchronizerName=syncerName)
  def withSchedulerName(self, schedName):
    return self._withParams(schedulerName=schedName)

  def withLoc1(self, loc1):
    return self._withParams(loc1=loc1)
  def withLoc2(self, loc2):
    return self._withParams(loc2=loc2)
  def withLoc3(self, loc3):
    newOpts = dict(self.syncerOpts)
    newOpts["Loc3"] = loc3
    return self.withSyncerOpts(**newOpts)
  def withLoc4(self, loc4):
    newOpts = dict(self.syncerOpts)
    newOpts["Loc4"] = loc4
    return self.withSyncerOpts(**newOpts)

  def enabled(self):
    return self._withParams(linkWithOwnName=True)
  def enabledAs(self, linkName):
    return self._withParams(linkName=linkName)

  def withSchedOpts(self, **newOpts):
    return self._withParams(schedOpts=newOpts)
  def withSyncerOpts(self, **newOpts):
    return self._withParams(syncerOpts=newOpts)

  def write(self):
    format = self.kwParams.get("content", RuleFormat)
    fileContents = format.format(
        loc1=self.loc1,
        loc2=self.loc2,
        sched=self.kwParams.get("schedulerName", ""),
        syncer=self.kwParams.get("synchronizerName", ""),
        schedOpts=iniFileFormatted(self.schedOpts),
        syncerOpts=iniFileFormatted(self.syncerOpts))

    self.ruleFilePath.write(fileContents)

    if "linkWithOwnName" in self.kwParams:
      self._writeSymlink(self.name)
    elif "linkName" in self.kwParams:
      self._writeSymlink(self.kwParams["linkName"])

    return self

  def _writeSymlink(self, linkName):
    local(self.configuredPaths.enabledDir).join(linkName).mksymlinkto(
        self.ruleFilePath)

  @property
  def loc1(self):
    if "loc1" not in self.kwParams:
      self.kwParams["loc1"] = self._validLoc()
    return self.kwParams["loc1"]
  @property
  def loc2(self):
    if "loc2" not in self.kwParams:
      self.kwParams["loc2"] = self._validLoc()
    return self.kwParams["loc2"]
  @property
  def schedOpts(self):
    return self.kwParams.get("schedOpts", dict())
  @property
  def syncerOpts(self):
    return self.kwParams.get("syncerOpts", dict())
  @property
  def ruleFilePath(self):
    return local(self.configuredPaths.rulesDir).join(self.name)

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return RuleBuilder(paths, sysPaths, foldersWriter, name, kwParams)
