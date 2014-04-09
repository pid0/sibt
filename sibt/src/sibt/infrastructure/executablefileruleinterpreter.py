import os
from sibt.configuration.exceptions import ConfigConsistencyException
from datetime import datetime, timezone

def normalizedLines(string):
  return [line.strip() for line in string.split("\n") if line.strip() != ""]

class ExecutableFileRuleInterpreter(object):
  def __init__(self, path, fileName, processRunner):
    self.name = fileName
    self.executable = path
    self.processRunner = processRunner

  def sync(self, options):
    self.processRunner.execute(self.executable, "sync",
        *self._keyValueEncode(options))
  def versionsOf(self, path, locNumber, options):
    times = normalizedLines(self.processRunner.getOutput(
        self.executable, "versions-of", path, str(locNumber), 
        *self._keyValueEncode(options)))
    return [self._parseTime(time) for time in times]

  def _parseTime(self, string):
    if all(c in "0123456789" for c in string):
      return datetime.utcfromtimestamp(int(string)).replace(tzinfo=timezone.utc)
    w3cString = string
    if "T" in w3cString and (w3cString[-6] == "+" or w3cString[-6] == "-"):
      w3cString = w3cString[:-3] + w3cString[-2:]
    return datetime.strptime(w3cString, "%Y-%m-%dT%H:%M:%S%z")

  def _keyValueEncode(self, dictionary):
    return ["{0}={1}".format(key, value) for (key, value) in 
        dictionary.items()]

  def availableOptions(self):
    return normalizedLines(self.processRunner.getOutput(
        self.executable, "available-options"))
  availableOptions = property(availableOptions)

  @classmethod
  def createWithFile(clazz, path, fileName, processRunner):
    if not clazz.isExecutable(path):
      raise ConfigConsistencyException("interpreter file not executable")

    return clazz(path, fileName, processRunner)
  @classmethod
  def isExecutable(self, path):
    return os.stat(path).st_mode & 0o100

