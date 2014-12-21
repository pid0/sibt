def initName(builder, name):
  return builder.withAnyName() if name is None else builder.withName(name)

def bashEchoLines(lines):
  return "\n".join("echo '{0}'".format(line) for line in lines)

class ConfigScenarioConstructor(object):
  def __init__(self, foldersWriter, interBuilder, schedBuilder, ruleBuilder):
    self.folders = foldersWriter
    self._anInter = interBuilder
    self._aSched = schedBuilder
    self._aRule = ruleBuilder

  def writeAnyRule(self, name, schedulerName, interpreterName, sysConfig=False):
    self.aRule().withName(name).withSchedulerName(schedulerName).\
        withInterpreterName(interpreterName).\
        asSysConfig(sysConfig).write()
  def writeAnyScheduler(self, name, sysConfig=False):
    self.aSched().withName(name).asSysConfig(sysConfig).write()
  def writeAnyInterpreter(self, name, sysConfig=False):
    self.anInter().withName(name).asSysConfig(sysConfig).write()

  def aSched(self, name=None):
    return initName(self._aSched, name).withAllFuncs()
  def anInter(self, name=None):
    return initName(self._anInter, name)
  def aRule(self, name=None):
    return initName(self._aRule, name)
  def aSysSched(self):
    return self.aSched().asSysConfig()
  def aSysInter(self):
    return self.anInter().asSysConfig()
  def aSysRule(self):
    return self.aRule().asSysConfig()

  def ruleWithSchedAndInter(self, name=None, isSysConfig=False):
    return self.aRule(name).asSysConfig(isSysConfig).\
        withScheduler(self.aSched().asSysConfig(isSysConfig).write()).\
        withInterpreter(self.anInter().asSysConfig(isSysConfig).write())
  def ruleWithInter(self, name=None):
    return self.aRule(name).withInterpreter(self.anInter().write())
  def ruleWithSched(self, name=None):
    return self.aRule(name).withScheduler(self.aSched().write())

  def interReturningVersions(self, forRelativeFile, ifWithinLoc1, ifWithinLoc2):
    return self.anInter().withBashCode("""
if [[ $1 = versions-of && $2 = {0} && $4 =~ ^Loc.*= ]]; then
  relativeToLoc=$3
  if [ $relativeToLoc = 1 ]; then
    {1}
  fi
  if [ $relativeToLoc = 2 ]; then
    {2}
  fi
fi""".format(forRelativeFile, bashEchoLines(ifWithinLoc1), 
  bashEchoLines(ifWithinLoc2)))

  def ruleWithEmptyLocs(self, name):
    return self.ruleWithSchedAndInter(name).withLoc1("").withLoc2("")
