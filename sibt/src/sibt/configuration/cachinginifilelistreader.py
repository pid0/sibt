import itertools
import os.path
import configparser
from sibt.configuration.exceptions import ConfigSyntaxException, \
    MissingConfigValuesException, NotReadableException

DefaultSec = configparser.DEFAULTSECT

def _flatten(xss):
  return [x for xs in xss for x in xs]

def _makeException(file, message):
  return ConfigSyntaxException("rule", None, message, file)

class CachingIniFileListReader(object):
  def __init__(self, includeDirs, allowedSections):
    self.includeDirs = includeDirs
    self.allowedSections = allowedSections + ["Global"]

  def _throwIfSectionIsNotAllowed(self, sectionNames, filePath):
    for sectionName in sectionNames:
      if sectionName not in self.allowedSections:
        raise _makeException(filePath, "unknown section [{0}]".format(
          sectionName))

  def _parserToSectionsDict(self, parser, filePath, raw=False):
    try:
      self._throwIfSectionIsNotAllowed(parser.sections(), filePath)

      for allowedSection in self.allowedSections:
        if not parser.has_section(allowedSection):
          parser.add_section(allowedSection)

      return dict((section, dict(parser.items(section, raw=raw))) for 
          section, _ in parser.items() if section != DefaultSec)
    except configparser.InterpolationMissingOptionError as ex:
      raise MissingConfigValuesException("rule", None, filePath) from ex

  def _parseFileWithParser(self, filePath, parser):
    try:
      with open(filePath, "r") as file:
        parser.read_file(itertools.chain(["[{0}]\n".format(DefaultSec)], file), 
            source=filePath)
    except configparser.Error as ex:
      raise _makeException(filePath, "wrong syntax") from ex

  def _findIncludeFile(self, name):
    path = None
    for directory in self.includeDirs:
      path = os.path.join(directory, name)
      if os.path.isfile(path):
        return path
    return path

  def _pathsImportedFrom(self, iniFilePath):
    with open(iniFilePath, "r") as iniFile:
      lines = [line.strip() for line in iniFile.readlines()]
      importedNames = [" ".join(line.split(" ")[1:]) for line in lines if 
          line.startswith("#import")]

    return [self._findIncludeFile(name + ".inc") for name in importedNames]

  def _recursivelyResolvedReadListOf(self, iniFilePath):
    ret = []
    for importedPath in self._pathsImportedFrom(iniFilePath):
      ret.extend(self._recursivelyResolvedReadListOf(importedPath))
    ret.append(iniFilePath)
    return ret

  def _removeUnderscoreOptions(self, sections):
    for name, section in sections.items():
      optNames = [optName for optName in section.keys() if 
          optName.startswith("_")]
      for optName in optNames:
        del section[optName]

  def _makeParser(self, defaultValues=None):
    ret = configparser.ConfigParser(empty_lines_in_values=False, 
        interpolation=configparser.BasicInterpolation())
    ret.optionxform = lambda key: key
    if defaultValues is not None:
      ret.read_dict({ DefaultSec: defaultValues })
    return ret

  def _readFilesInOrder(self, parser, paths):
    for path in paths:
      subParser = self._makeParser()
      self._parseFileWithParser(path, subParser)
      parser.read_dict(self._parserToSectionsDict(subParser, path, raw=True))

  def sectionsFromFiles(self, paths, instanceArgument):
    defaultValues = { "_instanceName": instanceArgument } if \
        instanceArgument is not None else None
    parser = self._makeParser(defaultValues=defaultValues)

    try: 
      self._readFilesInOrder(parser, _flatten(
        [self._recursivelyResolvedReadListOf(path) for path in paths]))
    except PermissionError as ex:
      raise NotReadableException(ex.filename) from ex

    ret = self._parserToSectionsDict(parser, paths[-1], raw=False)

    self._removeUnderscoreOptions(ret)
    return ret

