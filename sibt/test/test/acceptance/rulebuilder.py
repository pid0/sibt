from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local
from collections import namedtuple

RuleFormat = """
    [Rule]
    {ruleOpts}

    [Synchronizer]
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

_InstanceFile = namedtuple("_InstanceFile", [
  "name", "content", "mode"])

class RuleBuilder(ConfigObjectBuilder):
  def __init__(self, paths, sysPaths, foldersWriter, name, kwParams):
    super().__init__(paths, sysPaths, foldersWriter, name, kwParams)

  def _validLoc(self, name=None, isEmpty=False):
    return self.foldersWriter.validSynchronizerLoc(
        self.foldersWriter.uniqueFolderName() if name is None else name, 
        isEmpty)

  def withSynchronizer(self, syncer):
    return self._withParams(synchronizerName=syncer.name, synchronizer=syncer)
  def withScheduler(self, sched):
    return self._withParams(schedulerName=sched.name, scheduler=sched)
  def withSynchronizerName(self, syncerName):
    return self._withParams(synchronizerName=syncerName)
  def withSchedulerName(self, schedName):
    return self._withParams(schedulerName=schedName)

  def withLoc1(self, loc1):
    return self._withParams(loc1=loc1)
  def withLoc2(self, loc2):
    return self._withParams(loc2=loc2)
  def withNewValidLoc1(self, name=None, isEmpty=False):
    return self._withParams(loc1=self._validLoc(name, isEmpty))
  def withNewValidLoc2(self, name=None, isEmpty=False):
    return self._withParams(loc2=self._validLoc(name, isEmpty))
  def withNewValidLocs(self, locsAreEmpty=False):
    return self.withNewValidLoc1(isEmpty=locsAreEmpty).\
        withNewValidLoc2(isEmpty=locsAreEmpty)

  def withLoc3(self, loc3):
    newOpts = dict(self.syncerOpts)
    newOpts["Loc3"] = loc3
    return self.withSyncerOpts(**newOpts)
  def withLoc4(self, loc4):
    newOpts = dict(self.syncerOpts)
    newOpts["Loc4"] = loc4
    return self.withSyncerOpts(**newOpts)

  def enabled(self, instanceName="", instanceFileContent="", mode=None):
    return self._withParams(instanceFiles=self.instanceFiles + 
        [_InstanceFile(instanceName, instanceFileContent, mode)])
  def enabledWithUnreadableFile(self, instanceName):
    return self.enabled(instanceName, mode=0o200)

  def withSchedOpts(self, **newOpts):
    return self._withParams(schedOpts=newOpts)
  def withSyncerOpts(self, **newOpts):
    return self._withParams(syncerOpts=newOpts)
  def withOpts(self, **newOpts):
    ruleOpts = dict(self.ruleOpts)
    ruleOpts.update(newOpts)
    return self._withParams(ruleOpts=ruleOpts)
  def allowedForTestUser(self):
    return self.withOpts(AllowedForUsers="testUser")
  def allowedFor(self, name):
    return self.withOpts(AllowedForUsers=name)

  def write(self):
    format = self.kwParams.get("content", RuleFormat)
    fileContents = format.format(
        loc1=self.loc1,
        loc2=self.loc2,
        sched=self.kwParams.get("schedulerName", ""),
        syncer=self.kwParams.get("synchronizerName", ""),
        schedOpts=iniFileFormatted(self.schedOpts),
        syncerOpts=iniFileFormatted(self.syncerOpts),
        ruleOpts=iniFileFormatted(self.ruleOpts))

    self.ruleFilePath.write(fileContents)

    if "instanceFiles" in self.kwParams:
      for instanceFile in self.instanceFiles:
        self._writeInstanceFile(instanceFile)

    return self

  def _writeInstanceFile(self, instanceFile):
    path = local(self.configuredPaths.enabledDir).join(
        instanceFile.name + "@" + self.name)
    path.write(instanceFile.content)
    if instanceFile.mode is not None:
      path.chmod(instanceFile.mode)

  @property
  def instanceFiles(self):
    return self.kwParams.get("instanceFiles", [])
  @property
  def scheduler(self):
    return self.kwParams["scheduler"]
  @property
  def synchronizer(self):
    return self.kwParams["synchronizer"]
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
  def ruleOpts(self):
    return self.kwParams.get("ruleOpts", dict())
  @property
  def ruleFilePath(self):
    return local(self.configuredPaths.rulesDir).join(self.name)

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return RuleBuilder(paths, sysPaths, foldersWriter, name, kwParams)
