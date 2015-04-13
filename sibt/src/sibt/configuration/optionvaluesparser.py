from sibt.domain.location import buildLocationFromUrl

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
