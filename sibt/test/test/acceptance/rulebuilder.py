from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local

RuleFormat = """
    [Interpreter]
    Name = {inter}
    Loc1={loc1}
    Loc2={loc2}
    {interOpts}

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

  def withInterpreter(self, inter):
    return self._withParams(interpreterName=inter.name)
  def withScheduler(self, sched):
    return self._withParams(schedulerName=sched.name)
  def withInterpreterName(self, interName):
    return self._withParams(interpreterName=interName)
  def withSchedulerName(self, schedName):
    return self._withParams(schedulerName=schedName)

  def withLoc1(self, loc1):
    return self._withParams(loc1=loc1)
  def withLoc2(self, loc2):
    return self._withParams(loc2=loc2)

  def enabled(self):
    return self._withParams(linkWithOwnName=True)
  def enabledAs(self, linkName):
    return self._withParams(linkName=linkName)

  def withSchedOpts(self, **newOpts):
    return self._withParams(schedOpts=newOpts)
  def withInterOpts(self, **newOpts):
    return self._withParams(interOpts=newOpts)

  def write(self):
    format = self.kwParams.get("content", RuleFormat)
    fileContents = format if "{sched}" not in format else format.format(
        loc1=self.loc1,
        loc2=self.loc2,
        sched=self.kwParams["schedulerName"],
        inter=self.kwParams["interpreterName"],
        schedOpts=iniFileFormatted(self.kwParams.get("schedOpts", dict())),
        interOpts=iniFileFormatted(self.kwParams.get("interOpts", dict())))

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
  def ruleFilePath(self):
    return local(self.configuredPaths.rulesDir).join(self.name)

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return RuleBuilder(paths, sysPaths, foldersWriter, name, kwParams)
