import os
from sibt.configuration.exceptions import ConfigConsistencyException

class ExecutableFileRuleInterpreter(object):
  def __init__(self, path, fileName, processRunner):
    self.name = fileName
    self.executable = path
    self.processRunner = processRunner

  def sync(self, options):
    self.processRunner.execute(self.executable, "sync",
        *self.keyValueEncode(options))

  def keyValueEncode(self, dictionary):
    return ["{0}={1}".format(key, value) for (key, value) in 
        dictionary.items()]

  def availableOptions(self):
    output = self.processRunner.getOutput(self.executable, "available-options")
    return [line for line in output.split("\n") if line != ""]
  availableOptions = property(availableOptions)

  @classmethod
  def createWithFile(clazz, path, fileName, processRunner):
    if not clazz.isExecutable(path):
      raise ConfigConsistencyException("interpreter file not executable")

    return clazz(path, fileName, processRunner)
  @classmethod
  def isExecutable(self, path):
    return os.stat(path).st_mode & 0o100

