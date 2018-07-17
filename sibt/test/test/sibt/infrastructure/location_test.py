import pytest
from sibt.infrastructure.location import LocalLocation, RemoteLocation
from sibt.domain.exceptions import LocationInvalidException, \
    LocationNotAbsoluteException
from test.common.builders import writeFileTree
from test.common.assertutil import strToTest
from test.common.builders import remoteLocation

class LocationTest(object):
  def assertIsNotWithin(self, path, container):
    assert not self.locWithPath(container).contains(self.locWithPath(path))

  def assertIsWithin(self, path, container, **kwargs):
    self.assertLocIsWithin(self.locWithPath(path),
        self.locWithPath(container), **kwargs)
  def assertLocIsWithin(self, path, container, relPart=None):
    assert container.contains(path)
    if relPart is not None:
      assert container.relativePathTo(path) == relPart

  def test_shouldImplementEqualsAndHashCode(self):
    assert self.locWithPath("/tmp") == self.locWithPath("/tmp")
    assert hash(self.locWithPath("/tmp")) == hash(self.locWithPath("/tmp"))
    assert self.locWithPath("/var") != self.locWithPath("/tmp")

  def test_shouldNormalizeThePathWithoutChangingItsMeaning(self):
    assert self.locWithPath("//tmp///test/link/../foo//").path == \
        "/tmp/test/link/../foo"
    assert self.locWithPath("/tmp/./.").path == "/tmp"

  def test_shouldRecognizeIfAndHowItsPathContainsThePathOfAnotherLocation(self):
    self.assertIsWithin("/home", "/home/", relPart=".")
    self.assertIsWithin("/home//blah/quux", "/home", relPart="blah/quux")

    self.assertIsNotWithin("/mnt/foo", "/home")
    self.assertIsNotWithin("/home/foo-abc", "/home/foo")

    self.assertIsWithin("/anything", "/", relPart="anything")
    self.assertIsWithin("/", "/", relPart=".")

class Test_RemoteLocationTest(LocationTest):
  def locWithPath(self, path):
    return RemoteLocation("ssh", "user", "host", "5000", path)

  def test_shouldBeAbleToPrintItself(self):
    assert str(RemoteLocation("rsync", "user", "innsmouth", "5655", 
      "foo/")) == "rsync://user@innsmouth:5655/~/foo"

  def test_shouldRaiseExceptionIfHostOrPathIsMissing(self):
    with pytest.raises(LocationInvalidException) as ex:
      RemoteLocation("http", "", "", "", "/bar")
    assert "host" in ex.value.problem 
    assert strToTest(ex.value.stringRepresentation).shouldInclude("http", "bar")

    with pytest.raises(LocationInvalidException) as ex:
      RemoteLocation("http", "", "host", "", "")
    assert "path" in ex.value.problem

  def test_shouldTakeProtocolEtcIntoAccountWhenComparingWithRemoteLocs(self):
    assert remoteLocation(protocol="a") != remoteLocation(protocol="b")

  def test_shouldTreatExclusivelyRelativeOrAbsolutePathsAsCompatible(self):
    self.assertIsWithin("foo/bar", "foo", relPart="bar")
    self.assertIsNotWithin("foo/bar", "/foo")
    self.assertIsWithin("anything", ".", relPart="anything")
    self.assertIsWithin(".", ".", relPart=".")

  def test_shouldRequireProtocolsAndHostsToBeEqualForContainsTest(self):
    assert not remoteLocation(protocol="this").contains(
        remoteLocation(protocol="that"))
    assert not remoteLocation(host="this").contains(
        remoteLocation(host="that"))

  def test_shouldAlsoRequireLoginAndPortToBeEqualIfPathsAreRelative(self):
    assert not remoteLocation(login="this", path=".").contains(
        remoteLocation(login="that"))
    assert not remoteLocation(port="123", path=".").contains(
        remoteLocation(port="321", path="."))

    self.assertLocIsWithin(remoteLocation(port="123", path="/"),
        remoteLocation(port="321", path="/"), relPart=".")
    self.assertLocIsWithin(remoteLocation(login="this", path="/"),
        remoteLocation(login="that", path="/"), relPart=".")

  def test_shouldTreatSomeProtocolsAsEqualDependingOnIfPathsAreRelative(self):
    def shouldTreatEqually(protocol1, protocol2, onlyAbsolutePaths):
      self.assertLocIsWithin(remoteLocation(protocol=protocol1, path="/"),
          remoteLocation(protocol=protocol2, path="/"))
      loc1 = remoteLocation(protocol=protocol1, path=".")
      loc2 = remoteLocation(protocol=protocol2, path=".")
      if onlyAbsolutePaths:
        assert not loc1.contains(loc2)
      else:
        self.assertLocIsWithin(loc2, loc1)

    shouldTreatEqually("ssh", "scp", False)
    shouldTreatEqually("ssh", "sftp", False)
    shouldTreatEqually("ftp", "ssh", True)

class Test_LocalLocationTest(LocationTest):
  def locWithPath(self, path):
    return LocalLocation(path)

  def test_shouldRaiseExceptionIfPathIsNotAbsolute(self):
    with pytest.raises(LocationNotAbsoluteException):
      LocalLocation("only-relative")

    with pytest.raises(LocationNotAbsoluteException):
      LocalLocation("")

  def test_shouldFollowThePathUsingTheFilesystem(self):
    self.assertIsWithin("/home//foo/blah/..//blah/", "/home///foo/../foo",
        relPart="blah")

  def test_shouldInternallyResolveSymlinksOnItself(self, tmpdir):
    def inTmpdir(path):
      return str(tmpdir) + "/" + path

    writeFileTree(tmpdir, [".",
      "to-repo -> repo",
      ["repo",
        "to-without -> /home"]])

    self.assertIsWithin(inTmpdir("repo/foo"), inTmpdir("to-repo"), 
        relPart="foo")
    self.assertIsWithin(inTmpdir("repo"), inTmpdir("to-repo/"), relPart=".")

    self.assertIsNotWithin(inTmpdir("to-repo/to-without/"), inTmpdir("repo"))
    self.assertIsWithin(inTmpdir("to-repo/to-without"), inTmpdir("repo"), 
        relPart="to-without")
