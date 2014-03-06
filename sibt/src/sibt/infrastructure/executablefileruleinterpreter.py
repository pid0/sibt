import os

class ExecutableFileRuleInterpreter(object):
  def __init__(self, path, fileName, processRunner):
    self.name = fileName
    self.executable = path
    self.processRunner = processRunner

  def sync(self, rule):
    self.processRunner.execute(self.executable, rule.name)

  @classmethod
  def createWithFile(clazz, path, fileName, processRunner):
    if not clazz.isExecutable(path):
      raise Exception("interpreter file not executable")

    return clazz(path, fileName, processRunner)
  @classmethod
  def isExecutable(self, path):
    return os.stat(path).st_mode & 0o100

