import os
from datetime import datetime, timezone, timedelta
import time
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException, \
    ModuleFunctionNotImplementedException
import itertools 
from sibt.domain.port import Port
from sibt.infrastructure.optioninfoparser import OptionInfoParser

TimeFormat = "%Y-%m-%dT%H:%M:%S%z"

class FunctionModuleSynchronizer(object):
  def __init__(self, functions, name):
    self.functions = functions
    self.name = name
    self.formatter = FunctionModuleSynchronizer.TypedValuesFormatter()

  def sync(self, options):
    self._callFunction(self.functions.callVoid, "sync", options)

  def versionsOf(self, path, locNumber, options):
    times = self._callFunction(self.functions.callFuzzy, "versions-of", 
        options, path, locNumber)
    return [self._parseTime(time) for time in times]

  def restore(self, path, locNumber, version, destLocation, options):
    extendedOptions = dict(options)
    extendedOptions["Restore"] = destLocation
    self._callFunction(self.functions.callVoid, "restore", extendedOptions, 
        path, locNumber, version, 
        destLocation or "")

  def listFiles(self, path, locNumber, version, recursively, options):
    return self._callFunction(self.functions.callExact, "list-files", 
        options, path, str(locNumber), version, recursively)

  @property
  def availableOptions(self):
    parser = OptionInfoParser()
    return [parser.parse(optionString) for optionString in \
        self._callFunction(self.functions.callFuzzy, "available-options")]

  @property
  def ports(self):
    def lazyPortsOutput():
      for i in range(1, 101):
        yield self._callFunction(self.functions.callFuzzy, 
            "info-of-port", {}, i)

    infos = itertools.takewhile(lambda output: len(output) > 0, 
        lazyPortsOutput())
    return [Port(info[1:], info[0] == "1") for info in infos]

  @property
  def onePortMustHaveFileProtocol(self):
    return "one-must-be-file" in self._callFunction(self.functions.callFuzzy,
        "info-of-port", {}, "specials")

  def _callFunction(self, func, funcName, options=dict(), *positionalArgs):
    try:
      return func(funcName, self.formatter.formatArgs(positionalArgs),
          self.formatter.formatOptions(options))
    except ModuleFunctionNotImplementedException as ex:
      raise SynchronizerFuncNotImplementedException(self.name, ex.funcName)\
        from ex.__cause__

  def _parseTime(self, string):
    if all(c in "0123456789" for c in string):
      return datetime.utcfromtimestamp(int(string)).replace(tzinfo=timezone.utc)
    w3cString = string
    if "T" in w3cString and (w3cString[-6] == "+" or w3cString[-6] == "-"):
      w3cString = w3cString[:-3] + w3cString[-2:]
    return datetime.strptime(w3cString, TimeFormat)

  class TypedValuesFormatter(object):
    def formatArgs(self, args):
      return [self._formatValue(arg) for arg in args]

    def formatOptions(self, options):
      ret = dict(options)
      keysBeforeFormatting = list(options.keys())
      for key in keysBeforeFormatting:
        value = ret[key]
        ret[key] = self._formatValue(value)
        if hasattr(value, "protocol"):
          self._addLocationOptions(ret, key, value)
          if hasattr(value, "login"):
            self._addRemoteLocOptions(ret, key, value)
      return ret

    def _addLocationOptions(self, options, key, location):
      options[key + "Protocol"] = location.protocol
      options[key + "Path"] = location.path

    def _addRemoteLocOptions(self, options, key, location):
      options[key + "Login"] = location.login
      options[key + "Host"] = location.host
      options[key + "Port"] = location.port

    def _posixTimestampOf(self, timeObj):
      return int(time.mktime(timeObj.astimezone(None).timetuple()))

    def _formatValue(self, value):
      if isinstance(value, bool):
        return "1" if value else "0"
      if isinstance(value, timedelta):
        return str(int(value.total_seconds()))
      if isinstance(value, datetime):
        return str(self._posixTimestampOf(value))
      return str(value)

