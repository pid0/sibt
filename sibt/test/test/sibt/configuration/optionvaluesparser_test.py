import pytest
from sibt.domain.exceptions import LocationInvalidException
from sibt.configuration.optionvaluesparser import parseLocation

def test_shouldExactlyRecognizeSyntacticSugarForSSHLocations():
  loc = parseLocation("foo:/bar:quux")
  assert loc.protocol == "ssh"
  assert loc.host == "foo"
  assert loc.path == "/bar:quux"

  loc = parseLocation("yeah@host:relative/a://b/")
  assert loc.protocol == "ssh"
  assert loc.login == "yeah"
  assert loc.path == "relative/a:/b"

  loc = parseLocation("/foo:bar")
  assert loc.protocol == "file"

  loc = parseLocation("user@host-of-syntactic-sugar:")
  assert loc.protocol == "ssh"
  assert loc.path == "."
