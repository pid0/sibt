import pytest
from sibt.infrastructure import collectFilesInDirs

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.folder1 = tmpdir.join("folder1")
    self.folder1.mkdir()
    self.folder2 = tmpdir.join("folder2")
    self.folder2.mkdir()

    self.name1 = "file1"
    self.name2 = "some-file2"
    self.name3 = "bar"

  def writeFiles(self):
    self.folder1.join(self.name1).write("")
    self.folder1.join(self.name2).write("")
    self.folder2.join(self.name3).write("")

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_collectFuncShouldCallFunctionForEachFileInDirsAndCollectResultsInASet(
    fixture):
  fixture.writeFiles()
  assert collectFilesInDirs(
      [str(fixture.folder1), str(fixture.folder2)], 
      lambda path, fileName: (path, fileName)) == {
          (str(fixture.folder1) + "/" + fixture.name1, fixture.name1),
          (str(fixture.folder1) + "/" + fixture.name2, fixture.name2),
          (str(fixture.folder2) + "/" + fixture.name3, fixture.name3)}

def test_collectFunctionShouldLeaveOutNoneValues(fixture):
  fixture.writeFiles()
  assert collectFilesInDirs([str(fixture.folder1)], lambda _, name: 
      "ab" if name == fixture.name1 else None) == {"ab"}

