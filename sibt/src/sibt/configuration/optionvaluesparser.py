from sibt.domain.location import buildLocationFromUrl
from sibt.infrastructure import types
from datetime import timedelta
from sibt.configuration.exceptions import OptionParseError, OptionParseException
from sibt.domain.exceptions import LocationInvalidException

class _ParseException(Exception):
  def __init__(self, expectedType, message):
    self.expectedType = expectedType
    self.message = message

class OptionValuesParser(object):
  def parseOptions(self, availableInfos, options):
    namesToOptInfos = dict((info.name, info) for info in availableInfos)
    ret= dict()

    parseErrors = []

    for optName in options:
      try:
        ret[optName] = options[optName] if optName not in namesToOptInfos else \
            self._parseOption(options[optName], 
                namesToOptInfos[optName].optionType)
      except _ParseException as ex:
        parseErrors.append(OptionParseError(optName, options[optName],
          ex.expectedType, ex.message))

    if len(parseErrors) > 0:
      raise OptionParseException(parseErrors)
    
    return ret

  def _parseOption(self, string, optType):
    if optType is types.Positive:
      return self._parsePositive(string)

    if optType is types.Bool:
      return self._parseBool(string)

    if optType is types.TimeDelta:
      return self._parseTimeDelta(string)

    if optType is types.File:
      return self._wrapLocInvalidEx(
          lambda: buildLocationFromUrl("file://" + string), "local file")

    if optType is types.Location:
      return self._wrapLocInvalidEx(lambda: parseLocation(string), 
          "local path/URL")

    if isinstance(optType, types.Enum):
      for element in optType.values:
        if string.strip().lower() == element.name.lower():
          return element
      raise _ParseException("valid choice", "it's not " + 
          "/".join(value.name for value in optType.values))

    return string

  def _parseBool(self, string):
    if string.strip().lower() in ["yes", "on", "1", "true"]:
      return True
    if string.strip().lower() in ["no", "off", "0", "false"]:
      return False
    raise _ParseException("truth value", 
        "it's not yes/no, on/off, 1/0, or true/false")

  def _parsePositive(self, string):
    expectedType = "positive number"
    try:
      ret = int(string)
    except ValueError:
      raise _ParseException(expectedType, "it's no integer")
    if ret == 0:
      raise _ParseException(expectedType, "it's zero")
    if ret < 0:
      raise _ParseException(expectedType, "it's negative")
    return ret

  def _wrapLocInvalidEx(self, func, typeDesc):
    try:
      return func()
    except LocationInvalidException as ex:
      raise _ParseException(typeDesc, str(ex))

  def _parseTimeDelta(self, string):
    typeDesc = "a time interval"
    unitNames = ["seconds", "minutes", "hours", "days", "weeks"]
    def splitField(string):
      firstNonDigit = next((i for i, c in 
        enumerate(string) if not (c.isdigit() or c == "." or c == "-")), None)
      if firstNonDigit is None or firstNonDigit == 0:
        raise _ParseException(typeDesc, "units must follow numbers")
      else:
        try:
          value = float(string[:firstNonDigit])
        except ValueError:
          raise _ParseException(typeDesc, "‘{0}’ is no number".format(
            string[:firstNonDigit]))
        if value < 0:
          raise _ParseException(typeDesc, "‘{0}’ is negative".format(value))
        unitName = string[firstNonDigit:].lower()
        for existingUnit in unitNames:
          if existingUnit.startswith(unitName):
            return existingUnit, value
        raise _ParseException(typeDesc, "{0} is an unknown unit".format(
          unitName))

    def contractFields(fields, contracted):
      if len(fields) == 0:
        return contracted
      elif len(fields) == 1:
        return contracted + fields
      else:
        if not fields[1][0].isdigit():
          return contractFields(fields[2:], 
              contracted + [fields[0] + fields[1]])
        else:
          return contractFields(fields[1:], contracted + [fields[0]])

    fields = [field for field in string.split(" ") if len(field) > 0]

    unitsWithNumbers = [splitField(string) for string in 
        contractFields(fields, [])]
    constructorDict = dict()
    for unit, value in unitsWithNumbers:
      if unit in constructorDict:
        raise _ParseException(typeDesc, "a unit is used twice")
      constructorDict[unit] = value
    return timedelta(**constructorDict)

def parseLocation(string):
  protocolSeparatorPos = string.find("://")
  colonPos = string.find(":")
  slashPos = string.find("/")

  if protocolSeparatorPos != -1 and protocolSeparatorPos < slashPos:
    return buildLocationFromUrl(string)
  elif colonPos != -1 and (colonPos < slashPos or slashPos == -1):
    split = tuple(string.split(":"))
    hostAndLogin, path = split[0], ":".join(split[1:])
    if not path.startswith("/"):
      path = "/~/" + path
    return buildLocationFromUrl("ssh://{0}{1}".format(hostAndLogin, path))
  else:
    return buildLocationFromUrl("file://" + string)
