from sibt.infrastructure import types
from sibt.domain.optioninfo import OptionInfo
from sibt.infrastructure.exceptions import ParseException

class OptionInfoParser(object):
  def parse(self, string):
    parts = string.split(" ")
    if len(parts) > 2:
      raise ParseException(string, "option name may not contain a space")

    typeString, name = ("s", string) if len(parts) == 1 else \
        (parts[0], parts[1])

    return OptionInfo(name, self._identifierToType(typeString))

  def _identifierToType(self, identifier):
    if "|" in identifier:
      return types.Enum(*identifier.split("|"), equatableToNames=True)

    try:
      return dict(s=types.String,
          b=types.Bool,
          t=types.TimeDelta,
          f=types.File,
          p=types.Positive)[identifier]
    except KeyError as ex:
      raise ParseException(identifier, "unknown option type") from ex

