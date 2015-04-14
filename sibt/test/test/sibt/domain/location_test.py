import pytest
from sibt.domain.location import buildLocationFromUrl
from sibt.infrastructure.location import LocalLocation, RemoteLocation
from sibt.domain.exceptions import LocationInvalidException

def assertIsRemote(url, expectedProtocol, expectedLogin, expectedHost,
    expectedPort, expectedPath):
  loc = buildLocationFromUrl(url)

  assert isinstance(loc, RemoteLocation)
  assert loc.protocol == expectedProtocol
  assert loc.login == expectedLogin
  assert loc.host == expectedHost
  assert loc.port == expectedPort
  assert loc.path == expectedPath


def test_shouldSimplyRemoveThePrefixFromFileUrls():
  loc = buildLocationFromUrl("file:///user@host:23/foo/")
  assert isinstance(loc, LocalLocation)
  assert str(loc) == "/user@host:23/foo"

def test_shouldProperlyParseThePartsOfARemoteUrl():
  assertIsRemote("ssh://host/", "ssh", "", "host", "", "/")

  assertIsRemote("+*.://edgar@host/foo", "+*.", "edgar", "host", "", "/foo")
  assertIsRemote("foo://where/@a://b", "foo", "", "where", "", "/@a:/b")

  ipv6 = "2001:0db8:85a3:0042:1000:8a2e:0370:7334"
  assertIsRemote("rsync://a@" + ipv6 + ":2345/a/b", 
      "rsync", "a", ipv6, "2345", "/a/b")

  assertIsRemote("http://a:b/", "http", "", "a:b", "", "/")

def test_shouldParsePathsStartingWithATildeAsRelative():
  assertIsRemote("foo://where?/~/.kde4/share/apps/",
      "foo", "", "where?", "", ".kde4/share/apps")
  assertIsRemote("a://b/~/",
      "a", "", "b", "", ".")

def test_shouldRaiseExceptionIfUrlHasAWrongFormat():
  with pytest.raises(LocationInvalidException):
    buildLocationFromUrl("http:///path")
  with pytest.raises(LocationInvalidException):
    buildLocationFromUrl("http://host")

  with pytest.raises(LocationInvalidException) as ex:
    buildLocationFromUrl("/path")
  assert ex.value.stringRepresentation == "/path"
