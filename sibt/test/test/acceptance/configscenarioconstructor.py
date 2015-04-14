def initName(builder, name):
  return builder.withAnyName() if name is None else builder.withName(name)

def bashEchoLines(lines):
  return "\n".join("echo '{0}'".format(line) for line in lines)

class ConfigScenarioConstructor(object):
  def __init__(self, foldersWriter, syncerBuilder, schedBuilder, ruleBuilder):
    self.folders = foldersWriter
    self._aSyncer = syncerBuilder
    self._aSched = schedBuilder
    self._aRule = ruleBuilder

  def writeAnyRule(self, name, schedulerName, synchronizerName, 
      sysConfig=False):
    self.aRule().withName(name).withSchedulerName(schedulerName).\
        withSynchronizerName(synchronizerName).\
        asSysConfig(sysConfig).write()
  def writeAnyScheduler(self, name, sysConfig=False):
    self.aSched().withName(name).asSysConfig(sysConfig).write()
  def writeAnySynchronizer(self, name, sysConfig=False):
    self.aSyncer().withName(name).asSysConfig(sysConfig).write()

  def aSched(self, name=None):
    return initName(self._aSched, name).withAllFuncs()
  def aSyncer(self, name=None):
    return initName(self._aSyncer, name)
  def aRule(self, name=None):
    return initName(self._aRule, name)
  def aSysSched(self):
    return self.aSched().asSysConfig()
  def aSysSyncer(self):
    return self.aSyncer().asSysConfig()
  def aSysRule(self):
    return self.aRule().asSysConfig()

  def ruleWithSchedAndSyncer(self, name=None, isSysConfig=False):
    return self.aRule(name).asSysConfig(isSysConfig).\
        withScheduler(self.aSched().asSysConfig(isSysConfig).write()).\
        withSynchronizer(self.aSyncer().asSysConfig(isSysConfig).write())
  def ruleWithSyncer(self, name=None):
    return self.aRule(name).withSynchronizer(self.aSyncer().write())
  def ruleWithSched(self, name=None):
    return self.aRule(name).withScheduler(self.aSched().write())

  def syncerReturningVersions(self, forRelativeFile, ifWithinLoc1, 
      ifWithinLoc2):
    return self.aSyncer().withBashCode("""
if [ $1 = info-of-port ]; then
  if [[ $2 != extra && $2 -lt 3 ]]; then
    echo 0
    echo file
    echo ssh
  fi
elif [[ $1 = versions-of && $2 = {0} && $4 =~ ^Loc.*= ]]; then
  relativeToLoc=$3
  if [ $relativeToLoc = 1 ]; then
    {1}
  fi
  if [ $relativeToLoc = 2 ]; then
    {2}
  fi
else exit 200; fi""".format(forRelativeFile, bashEchoLines(ifWithinLoc1), 
  bashEchoLines(ifWithinLoc2)))

  def ruleWithNonExistentLocs(self, name):
    return self.ruleWithSchedAndSyncer(name).withLoc1("/abc").withLoc2("/efg")
