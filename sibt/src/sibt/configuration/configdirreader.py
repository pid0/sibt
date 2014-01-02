from sibt.configuration.backuprule import BackupRule
import os
from sibt.configuration.configuration import Configuration
from datetime import timedelta, datetime
from sibt.configuration.timerange import TimeRange
from sibt.configuration.configparseexception import ConfigParseException


class ConfigDirReader(object):
  TimeOfDayRestrictionKey = "avoid time of day from"
  
  def __init__(self, configDir):
    self.configDir = configDir
    
  def read(self):
    fileNames = os.listdir(self.configDir)
    return Configuration(set([self._readRuleFile(fileName) for fileName in 
      fileNames if not (fileName.startswith("N") or 
        fileName == "global.conf")]), self._readGlobalConf())
  
  def _readGlobalConf(self):
    fileName = os.path.join(self.configDir, "global.conf")
    if not os.path.exists(fileName):
      return None
    
    with open(os.path.join(self.configDir, "global.conf"), 'r') as file:
      lines = self._readNonEmptyLinesFromFile(file)
      for line in lines:
        if line.startswith(ConfigDirReader.TimeOfDayRestrictionKey):
          return self._parseTimeRange(
            line[len(ConfigDirReader.TimeOfDayRestrictionKey):], "global.conf")
          
      return None
    
  def _parseTimeRange(self, string, fileName):
    if "to" not in string:
      raise ConfigParseException(fileName,
      "error parsing time of day restriction: format: from ... to")
      
    parts = [part.strip() for part in string.split("to")]
    return TimeRange(self._parseTimeOfDay(parts[0], fileName), 
      self._parseTimeOfDay(parts[1], fileName))
    
  def _parseTimeOfDay(self, string, fileName):
    try: return datetime.strptime(string, "%H:%M").time()
    except BaseException as ex: raise ConfigParseException(fileName,
      "error parsing time of day restriction: format %H:%M") from ex
  
  def _readNonEmptyLinesFromFile(self, file):
    lines = [line.strip('\n').strip() for line in file.readlines()]
    return [line for line in lines if len(line) != 0]
  
  def _readRuleFile(self, fileName):
    fullFileName = os.path.join(self.configDir, fileName) 
    
    with open(fullFileName, 'r') as file:
      nonEmptyLines = self._readNonEmptyLinesFromFile(file)
      
      if len(nonEmptyLines) > 4:
        raise ConfigParseException(fileName, "superfluous lines")
      
      return BackupRule(fileName, nonEmptyLines[0], nonEmptyLines[1], 
        nonEmptyLines[2], self._parseInterval(nonEmptyLines[3], fileName) 
        if len(nonEmptyLines) > 3 else None)
      
  def _parseInterval(self, string, fileName):
    interval = string.split(' ')[-1]
    try:
      magnitude = int(interval[:-1])
    except BaseException as ex:
      raise ConfigParseException(fileName, 
        "error parsing interval specification") from ex
    unit = interval[-1]
    
    if magnitude <= 0:
      raise ConfigParseException(fileName, "interval specified was less than" +
        " or equal to 0")
    
    if unit == 'd':
      return timedelta(days=magnitude)
    elif unit == 'w':
      return timedelta(weeks=magnitude)
    else:
      raise ConfigParseException(fileName, 
        'invalid interval unit "' + unit + '"')