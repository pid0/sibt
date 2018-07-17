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

from sibt.infrastructure.location import LocalLocation, RemoteLocation
from sibt.domain.exceptions import LocationInvalidException
import re

UrlRegex = re.compile((r"^(?P<protocol>.+?)://"
  r"((?P<login>[^@/]+)@)?"
  r"(?P<host>[^/]+?)?"
  r"(:(?P<port>[0-9]+))?"
  r"(?P<path>/.*)?$"))

def buildLocationFromUrl(string):
  if string.startswith("file://"):
    return LocalLocation(string[7:])

  regexMatch = UrlRegex.match(string)

  if regexMatch is None:
    raise LocationInvalidException(string, "is not a valid url")

  path = regexMatch.group("path") or ""
  if path.startswith("/~/"):
    path = path[3:]
    if path == "":
      path = "."

  return RemoteLocation(regexMatch.group("protocol"),
      regexMatch.group("login") or "",
      regexMatch.group("host") or "",
      regexMatch.group("port") or "",
      path)

