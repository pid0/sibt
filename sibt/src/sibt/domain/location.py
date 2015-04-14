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

