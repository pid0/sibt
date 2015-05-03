import os
from datetime import datetime, timezone
import time
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException, \
    ModuleFunctionNotImplementedException
import itertools 
from sibt.domain.port import Port

TimeFormat = "%Y-%m-%dT%H:%M:%S%z"

class FunctionModuleSynchronizer(object):
  def __init__(self, functions, name):
    self.functions = functions
    self.name = name

  def sync(self, options):
    self._callFunction(self.functions.callVoid, "sync", options)

  def versionsOf(self, path, locNumber, options):
    times = self._callFunction(self.functions.callFuzzy, "versions-of", 
        options, path, str(locNumber))
    return [self._parseTime(time) for time in times]

  def restore(self, path, locNumber, version, destLocation, options):
    extendedOptions = dict(options)
    extendedOptions["Restore"] = destLocation
    self._callFunction(self.functions.callVoid, "restore", extendedOptions, 
        path, str(locNumber), self._posixTimestampOf(version), 
        destLocation or "")

    #TODO: leave 0, 1 formatting to formatter
  def listFiles(self, path, locNumber, version, recursively, options):
    return self._callFunction(self.functions.callExact, "list-files", 
        options, path, str(locNumber), self._posixTimestampOf(version),
        "1" if recursively else "0")

  @property
  def availableOptions(self):
    return self._callFunction(self.functions.callFuzzy, "available-options")

  @property
  def ports(self):
    def lazyPortsOutput():
      for i in range(1, 101):
        yield self._callFunction(self.functions.callFuzzy, 
            "info-of-port", {}, str(i))

    infos = itertools.takewhile(lambda output: len(output) > 0, 
        lazyPortsOutput())
    return [Port(info[1:], info[0] == "1") for info in infos]

  @property
  def onePortMustHaveFileProtocol(self):
    return "one-must-be-file" in self._callFunction(self.functions.callFuzzy,
        "info-of-port", dict(), "specials")

  def _callFunction(self, func, funcName, options=dict(), *positionalArgs):
    try:
      formattedOptions = dict(options)
      keysBeforeFormatting = list(formattedOptions.keys())
      for key in keysBeforeFormatting:
        value = formattedOptions[key]
        formattedOptions[key] = str(value)
        if hasattr(value, "protocol"):
          formattedOptions[key + "Protocol"] = value.protocol
          formattedOptions[key + "Path"] = value.path
          if hasattr(value, "login"):
            formattedOptions[key + "Login"] = value.login
            formattedOptions[key + "Host"] = value.host
            formattedOptions[key + "Port"] = value.port

      return func(funcName, [str(arg) for arg in positionalArgs], 
          formattedOptions)
    except ModuleFunctionNotImplementedException as ex:
      raise SynchronizerFuncNotImplementedException(self.name, ex.funcName)\
        from ex.__cause__

  def _posixTimestampOf(self, version):
    return int(time.mktime(version.astimezone(None).timetuple()))

  def _parseTime(self, string):
    if all(c in "0123456789" for c in string):
      return datetime.utcfromtimestamp(int(string)).replace(tzinfo=timezone.utc)
    w3cString = string
    if "T" in w3cString and (w3cString[-6] == "+" or w3cString[-6] == "-"):
      w3cString = w3cString[:-3] + w3cString[-2:]
    return datetime.strptime(w3cString, TimeFormat)

