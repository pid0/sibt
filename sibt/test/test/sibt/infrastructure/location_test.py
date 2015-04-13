import pytest
from sibt.infrastructure.location import LocalLocation, RemoteLocation
from sibt.domain.exceptions import LocationInvalidException
from test.common.builders import writeFileTree
from test.common.assertutil import strToTest

class Test_RemoteLocationTest(object):
#TODO share 2 tests; 
  def test_shouldBeAbleToPrintItself(self):
    str(RemoteLocation("rsync", "user", "innsmouth", "5655", "/foo/")) == \
        "rsync://user@innsmouth:5655/foo"

  def test_shouldRaiseExceptionIfHostOrPathIsMissing(self):
    with pytest.raises(LocationInvalidException) as ex:
      RemoteLocation("http", "", "", "", "/bar")
    assert "host" in ex.value.problem 
    assert strToTest(ex.value.stringRepresentation).shouldInclude("http", "bar")

    with pytest.raises(LocationInvalidException) as ex:
      RemoteLocation("http", "", "host", "", "")
    assert "path" in ex.value.problem

class Test_LocalLocationTest(object):
  def assertIsNotWithin(self, path, container):
    assert not LocalLocation(container).contains(LocalLocation(path))

  def assertIsWithin(self, path, container, relPart=None):
    assert LocalLocation(container).contains(LocalLocation(path))
    if relPart is not None:
      assert LocalLocation(container).relativePathTo(LocalLocation(path)) == \
          relPart


  def test_shouldNormalizeThePathWithoutChangingItsMeaning(self):
    assert str(LocalLocation("//tmp///test/link/../foo//")) == \
        "/tmp/test/link/../foo"
    assert str(LocalLocation("/tmp/./.")) == "/tmp"

  def test_shouldRaiseExceptionIfPathIsNotAbsolute(self):
    with pytest.raises(LocationInvalidException) as ex:
      LocalLocation("only-relative")
    assert "not absolute" in ex.value.problem

    with pytest.raises(LocationInvalidException):
      LocalLocation("")

  def test_shouldRecognizeIfAndHowItContainsAnotherLocation(self):
    self.assertIsWithin("/home", "/home/", relPart=".")
    self.assertIsWithin("/home/blah/quux", "/home", relPart="blah/quux")
    self.assertIsWithin("/home//foo/blah/..//blah/", "/home///foo/../foo",
        relPart="blah")

    self.assertIsNotWithin("/mnt/foo", "/home")
    self.assertIsNotWithin("/home/foo-abc", "/home/foo")

    self.assertIsWithin("/anything", "/", relPart="anything")

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
