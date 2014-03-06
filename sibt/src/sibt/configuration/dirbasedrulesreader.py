from sibt.domain.syncrule import SyncRule
import os
from datetime import timedelta, datetime
from sibt.configuration.configparseexception import ConfigParseException
from sibt.infrastructure import collectFilesInDirs

class DirBasedRulesReader(object):
  def __init__(self, rulesDir):
    self.rulesDir = rulesDir
    
  def read(self):
    return collectFilesInDirs([self.rulesDir], self._readRule)

  def _readRule(self, path, fileName):
    with open(path, "r") as ruleFile:
      interpreterName, schedulerName = ruleFile.readlines()[0:2]
    return SyncRule(fileName, schedulerName.strip(), interpreterName.strip())

