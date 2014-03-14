from sibt.domain.syncrule import SyncRule
import os
import os.path
from datetime import timedelta, datetime
from sibt.configuration.exceptions import ConfigSyntaxException
from sibt.configuration.exceptions import ConfigConsistencyException
from sibt.infrastructure import collectFilesInDirs
from configparser import ConfigParser
import itertools

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

  def _overrideSections(self, sections):
    keyValuePairs = (section.items() for section in sections)
    concatenatedPairs = itertools.chain(*keyValuePairs)

    return dict(pair for pair in itertools.chain(concatenatedPairs))

  def _overrideSectionDictsLastHighestPrecedence(self, dicts):
    presentSections = set(sectionName for readDict in dicts for sectionName in 
        readDict.keys())
    ret = dict()
    for sectionName in presentSections:
      ret[sectionName] = self._overrideSections(section[1] for readDict in
          dicts for section in readDict.items() if section[0] == sectionName)

    return ret


  def _readSectionsDict(self, path):
    parser = ConfigParser(empty_lines_in_values=False, interpolation=None)
    parser.optionxform = lambda key: key

    with open(path, "r") as ruleFile:
      lines = [line.strip() for line in ruleFile.readlines()]
      importedNames = [" ".join(line.split(" ")[1:]) for line in lines if 
          line.startswith("#import")]

    try:
      parser.read(path)
    except Exception as ex:
      raise ConfigSyntaxException(path, "error parsing ini syntax") from ex

    presetDicts = [self._readSectionsDict(os.path.join(
        self.rulesDir, name + ".inc")) for name in importedNames]

    return self._overrideSectionDictsLastHighestPrecedence(presetDicts +
        [parser])

  def _readRuleFile(self, path, fileName):
    if "," in fileName or "@" in fileName:
      raise ConfigSyntaxException(path, 
          "invalid character (, and @) in rule name")
    if fileName.endswith(".inc"):
      return None
    
    sections = self._readSectionsDict(path)

    if not self._exactlyKnownSectionsPresentIn(sections):
      raise ConfigSyntaxException(path, 
          "sections [Interpreter] and [Scheduler] are required")

    try:
      ret = self.factory.build(fileName, dict(sections[SchedSec]), 
          dict(sections[InterSec]), self._isEnabled(fileName))
    except ConfigConsistencyException as ex:
      raise ConfigSyntaxException(path, "rule consistency error") from ex

    return ret

  def _exactlyKnownSectionsPresentIn(self, parsed):
    if not all(name in parsed.keys() for name in [InterSec, SchedSec]):
      return False
    return len(parsed.keys()) == 3

