import os
from sibt.configuration.exceptions import ConfigConsistencyException
from datetime import datetime, timezone
import time
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException
from sibt.infrastructure.interpreterfuncnotimplementedexception import \
    InterpreterFuncNotImplementedException

def normalizedLines(lines):
  return [line.strip() for line in lines if line.strip() != ""]
TimeFormat = "%Y-%m-%dT%H:%M:%S%z"

class ExecutableFileRuleInterpreter(object):
  def __init__(self, path, fileName, processRunner):
    self.name = fileName
    self.executable = path
    self.processRunner = processRunner


  def sync(self, options):
    self._execute("sync", *self._keyValueEncode(options))

  def versionsOf(self, path, locNumber, options):
    times = normalizedLines(self._getOutput("versions-of", path, 
      str(locNumber), *self._keyValueEncode(options)))
    return [self._parseTime(time) for time in times]

  def restore(self, path, locNumber, version, dest, options):
    w3c, timestamp = self._encodeTime(version)
    self._execute("restore", path, str(locNumber), w3c, 
        str(timestamp), dest or "", *self._keyValueEncode(options))

  def listFiles(self, path, locNumber, version, recursively, options):
    w3c, timestamp = self._encodeTime(version)
    return self._getOutput("list-files", path, str(locNumber), w3c, 
        str(timestamp), "1" if recursively else "0",
        *self._keyValueEncode(options), evaluate=False, delimiter="\0")

  @property
  def availableOptions(self):
    return normalizedLines(self._getOutput("available-options"))

  @property
  def writeLocIndices(self):
    return [int(line) for line in normalizedLines(self._getOutput("writes-to"))]

  def _getOutput(self, funcName, *args, evaluate=True, **kwargs):
    def call():
      ret = self.processRunner.getOutput(self.executable, funcName, *args, 
          **kwargs)
      return list(ret) if evaluate else ret
    return self._catchNotImplemented(call, funcName)
  def _execute(self, funcName, *args):
    return self._catchNotImplemented(
        lambda: self.processRunner.execute(self.executable, funcName, *args),
        funcName)

  def _catchNotImplemented(self, func, funcName):
    try:
      ret = func()
      return ret
    except ExternalFailureException as ex:
      if ex.exitStatus == 200:
        raise InterpreterFuncNotImplementedException(self.executable, funcName)\
          from ex
      else:
        raise ex


  def _encodeTime(self, version):
    timestamp = int(time.mktime(version.astimezone(None).timetuple()))
    w3cString = version.strftime(TimeFormat)
    w3cString = w3cString[:-2] + ":" + w3cString[-2:]
    return (w3cString, str(timestamp))

  def _parseTime(self, string):
    if all(c in "0123456789" for c in string):
      return datetime.utcfromtimestamp(int(string)).replace(tzinfo=timezone.utc)
    w3cString = string
    if "T" in w3cString and (w3cString[-6] == "+" or w3cString[-6] == "-"):
      w3cString = w3cString[:-3] + w3cString[-2:]
    return datetime.strptime(w3cString, TimeFormat)

  def _keyValueEncode(self, dictionary):
    return ["{0}={1}".format(key, value) for (key, value) in 
        dictionary.items()]

  @classmethod
  def createWithFile(clazz, path, fileName, processRunner):
    if not clazz.isExecutable(path):
      raise ConfigConsistencyException("interpreter",
          fileName, "file not executable", file=path)

    return clazz(path, fileName, processRunner)
  @classmethod
  def isExecutable(self, path):
    return os.stat(path).st_mode & 0o100

