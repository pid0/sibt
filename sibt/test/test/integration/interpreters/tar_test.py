import pytest
from test.integration.interpreters.interpretertest import \
    InterpreterTestFixture, IncrementalInterpreterTest
import tarfile
from test.common.assertutil import iterableContainsInAnyOrder
import os

class Fixture(InterpreterTestFixture):
  def __init__(self, tmpdir):
    self.load("tar", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def archiveContains(path, *matchers):
  with tarfile.open(str(path)) as tar:
    members = tar.getmembers()
    return iterableContainsInAnyOrder(members, *matchers) 

def archiveFileHasContents(archivePath, name, expectedContents):
  with tarfile.open(str(archivePath)) as tar:
    with tar.extractfile(name) as archivedFile:
      return archivedFile.read().decode() == expectedContents

class Test_TarTest(object):
  def test_shouldKeepAsManyArchivesAsSpecifiedAndCycleThroughThem(self, 
      fixture):
    assert "KeepCopies" in fixture.inter.availableOptions

    options = fixture.optsWith({ "KeepCopies": "3" })

    fixture.loc1.join(".file").write("foo")
    for _ in range(4):
      fixture.inter.sync(options)

    carrollQuote = "in a wonderland they lie"
    fixture.loc1.join("carroll").write(carrollQuote)
    fixture.inter.sync(options)

    assert archiveContains(fixture.loc2 / "ar0",
        lambda info: info.name == ".file")

    archives = (loc2File for loc2File in os.listdir(str(fixture.loc2)) if 
        loc2File.startswith("ar"))
    assert set(archives) == {"ar0", "ar1", "ar2"}

    assert archiveContains(fixture.loc2 / "ar1",
        lambda info: info.name == ".file",
        lambda info: info.name == "carroll")
    assert archiveFileHasContents(fixture.loc2 / "ar1", "carroll", carrollQuote)

  def test_shouldTellThatItWritesToLoc2(self, fixture):
    assert fixture.inter.writeLocIndices == [2]



#TODO
#should remember the time the backup was made (simply mtime?)
