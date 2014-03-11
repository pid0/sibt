from sibt.domain.syncrule import SyncRule
import os
import os.path
from datetime import timedelta, datetime
from sibt.configuration.exceptions import ConfigSyntaxException
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.infrastructure import collectFilesInDirs
from configparser import ConfigParser

InterSec = "Interpreter"
SchedSec = "Scheduler"

class DirBasedRulesReader(object):
  def __init__(self, rulesDir, enabledDir, factory):
    self.rulesDir = rulesDir
    self.enabledDir = enabledDir
    self.factory = factory
    
  def read(self):
    return collectFilesInDirs([self.rulesDir], self._readRuleFile)

  def _isEnabled(self, ruleName):
    linkPath = os.path.join(self.enabledDir, ruleName)
    return os.path.islink(linkPath) and \
        os.readlink(linkPath) == os.path.join(self.rulesDir, ruleName)

  def _readRuleFile(self, path, fileName):
    if "," in fileName or "@" in fileName:
      raise ConfigSyntaxException(path, 
          "invalid character (, and @) in rule name")
    parser = ConfigParser(empty_lines_in_values=False, interpolation=None)
    parser.optionxform = lambda key: key

    with open(path, "r") as ruleFile:
      try:
        parser.read_file(ruleFile)
      except Exception as ex:
        raise ConfigSyntaxException(path, "error parsing ini syntax") from ex

    try:
      ret = self.factory.build(fileName, dict(parser[SchedSec]), 
          dict(parser[InterSec]), self._isEnabled(fileName))
    except ConfigConsistencyException as ex:
      raise ConfigSyntaxException(path, "rule consistency error") from ex

    return ret

