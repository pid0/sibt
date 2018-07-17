# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

