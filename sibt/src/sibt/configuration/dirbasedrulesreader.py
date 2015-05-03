from sibt.domain.syncrule import SyncRule
import os
import os.path
from datetime import timedelta, datetime
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException, RuleNameInvalidException
from sibt.infrastructure import collectFilesInDirs
from configparser import ConfigParser, BasicInterpolation
import configparser
import itertools
import functools

InterSec = "Synchronizer"
SchedSec = "Scheduler"
DefaultSec = configparser.DEFAULTSECT
RequiredSections = [InterSec, SchedSec]
AllowedCustomSections = [InterSec, SchedSec]
AllowedSections = [DefaultSec] + AllowedCustomSections

def _makeException(file, message):
  return ConfigSyntaxException("rule", os.path.basename(file), message, file)

class DirBasedRulesReader(object):
  def __init__(self, rulesDir, enabledDir, factory, namePrefix):
    self.rulesDir = rulesDir
    self.enabledDir = enabledDir
    self.factory = factory
    self.namePrefix = namePrefix
    
  def read(self):
    return [rule for instancesList in collectFilesInDirs([self.rulesDir], 
      self._readInstancesFromBaseRule) for rule in instancesList]

  def _removeUnderscoreOptions(self, sections):
    for name, section in sections.items():
      optNames = [optName for optName in section.keys() if 
          optName.startswith("_")]
      for optName in optNames:
        del section[optName]

  def _parserToSectionsDict(self, parser, filePath, raw=False):
    try:
      for allowedSection in AllowedCustomSections:
        if not parser.has_section(allowedSection):
          parser.add_section(allowedSection)
      return dict((section, dict(parser.items(section, raw=raw))) for 
          section, _ in parser.items())
    except configparser.InterpolationMissingOptionError as ex:
      raise _makeException(filePath, "can't resolve options") from ex

  def _makeParser(self, defaultValues=None):
    ret = ConfigParser(empty_lines_in_values=False, 
        interpolation=BasicInterpolation())
    ret.optionxform = lambda key: key
    if defaultValues is not None:
      ret.read_dict({ DefaultSec: defaultValues })
    return ret

  def _parseFileWithParser(self, filePath, parser):
    try:
      with open(filePath, "r") as file:
        parser.read_file(itertools.chain(["[{0}]\n".format(DefaultSec)], file), 
            source=filePath)
    except configparser.Error as ex:
      raise _makeException(filePath, "wrong syntax") from ex

  def _parseRawSectionsDict(self, filePath):
    return self._parserToSectionsDict(
        self._parserOfIniFileWithImportsResolved(filePath), filePath, raw=True)

  def _parserOfIniFileWithImportsResolved(self, path):
    parser = self._makeParser()

    with open(path, "r") as ruleFile:
      lines = [line.strip() for line in ruleFile.readlines()]
      importedNames = [" ".join(line.split(" ")[1:]) for line in lines if 
          line.startswith("#import")]

    importedDicts = [self._parseRawSectionsDict(os.path.join(
        self.rulesDir, name + ".inc")) for name in importedNames]

    for importedDict in importedDicts:
      parser.read_dict(importedDict)

    self._parseFileWithParser(path, parser)

    return parser

  def _readInstancesFromBaseRule(self, baseRulePath, baseRuleName):
    if baseRuleName.endswith(".inc"):
      return None

    baseSections = self._parseRawSectionsDict(baseRulePath)
    
    instances =  collectFilesInDirs([self.enabledDir], functools.partial(
      self._buildRuleInstance, baseSections, baseRuleName, True))
    if len(instances) == 0:
      disabledRule = self._buildRuleInstance(baseSections, baseRuleName, False, 
        baseRulePath, "@" + baseRuleName)
      if disabledRule is not None:
        return [disabledRule]
    return instances

  def _buildRuleInstance(self, baseSectionsDict, baseRuleName, 
      isEnabled, path, fileName):
    if not fileName.endswith("@" + baseRuleName):
      return None

    variablePart = fileName[:-len("@" + baseRuleName)]
    instanceName = fileName[1:] if fileName.startswith("@") else fileName

    if instanceName.startswith("+"):
      raise RuleNameInvalidException(instanceName, "+", 
          furtherDescription="at the beginning")

    if isEnabled:
      parser = self._makeParser(defaultValues={ "_instanceName": variablePart })
    else:
      parser = self._makeParser()

    parser.read_dict(baseSectionsDict)
    if isEnabled:
      parser.read_dict(self._parseRawSectionsDict(path))

    try:
      sections = self._parserToSectionsDict(parser, path)
    except ConfigSyntaxException as ex:
      if isinstance(ex.__cause__, 
          configparser.InterpolationMissingOptionError) and not isEnabled:
        return None 
      raise

    self._throwIfSectionsSetIsInvalid(sections.keys(), path)
    self._removeUnderscoreOptions(sections)

    try:
      return self.factory.build(self.namePrefix + instanceName, 
          sections[SchedSec], 
          sections[InterSec], isEnabled)
    except ConfigConsistencyException as ex:
      ex.file = path
      raise

  def _throwIfSectionsSetIsInvalid(self, sectionNames, filePath):
    for sectionName in RequiredSections:
      if sectionName not in sectionNames:
        raise _makeException(filePath, "section [{0}] is required".format(
          sectionName))

    for sectionName in sectionNames:
      if sectionName not in AllowedSections:
        raise _makeException(filePath, "unknown section [{0}]".format(
          sectionName))

