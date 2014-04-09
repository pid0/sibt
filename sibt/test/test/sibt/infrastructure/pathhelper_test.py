import pytest
from sibt.infrastructure.pathhelper import isPathWithinPath, removeCommonPrefix

def test_shouldBeAbleToTellIfAPathIsWithinSomeAbsoluteOne(tmpdir):
  with tmpdir.as_cwd():
    assert isPathWithinPath("bar", str(tmpdir))
    assert not isPathWithinPath("../bar", str(tmpdir))
    assert not isPathWithinPath("bar", str(tmpdir.join("folder")))

  assert isPathWithinPath("/home/blah", "/home")
  assert isPathWithinPath("/home//foo/blah/..//blah/", "/home///foo")
  assert not isPathWithinPath("/mnt/foo", "/home")

def test_shouldBeAbleToRemoveContainerPrefixFromAPath(tmpdir):
  assert removeCommonPrefix("/home/foo//bar/", "/home/../home") == "foo/bar"
  with tmpdir.as_cwd():
    assert removeCommonPrefix("foo/bar", str(tmpdir)) == "foo/bar"

def test_shouldResolveSymlinksBeforePerformingOperations(tmpdir):
  pathLink = tmpdir.join("link")
  pathLink.mksymlinkto("/home/foo")
  containerLink = tmpdir.join("link2")
  containerLink.mksymlinkto("/home")
  assert isPathWithinPath(str(pathLink.join("bar")), 
      str(containerLink.join("foo")))
  assert not isPathWithinPath(str(pathLink), str(tmpdir))

  assert removeCommonPrefix("/home/foo/bar", str(pathLink)) == "bar"
  assert removeCommonPrefix(str(pathLink.join("bar")), "/home/foo") == "bar"
