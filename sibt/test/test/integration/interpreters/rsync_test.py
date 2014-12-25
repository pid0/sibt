import pytest
from test.integration.interpreters.interpretertest import \
    InterpreterTestFixture, MirrorInterpreterTest
import os
from datetime import datetime, timezone
from test.common.builders import anyUTCDateTime

class Fixture(InterpreterTestFixture):
  def __init__(self, tmpdir):
    self.load("rsync", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_RsyncTest(MirrorInterpreterTest):
  def rewriteLoc1PathForMirrorTest(self, path):
    if path.endswith("/"):
      return path[:-1]
    return path

  def test_shouldSimplyUseTheFilesModificationTimeAsVersion(self, fixture):
    someFile = fixture.loc1.join("file")
    someFile.write("")
    fixture.changeMTime(str(someFile), 23)
    options = fixture.optsWith(dict())

    fixture.inter.sync(options)

    expectedVersion = datetime(1970, 1, 1, 0, 0, 23, tzinfo=timezone.utc)
    assert fixture.inter.versionsOf("file", 1, options) == [expectedVersion]

    assert fixture.inter.versionsOf("does-not-exist", 1, options) == []
    assert fixture.inter.versionsOf("file", 2, options) == []

  def test_shouldSupportInsertingCustomRsyncOptionsWhenSyncing(self, fixture):
    assert "AdditionalSyncOpts" in fixture.inter.availableOptions

    fixture.loc1.join("file=a").write("")
    fixture.loc1.join("file=b").write("")

    fixture.inter.sync(fixture.optsWith({"AdditionalSyncOpts": 
        "--exclude *=a"}))

    assert os.listdir(str(fixture.loc2)) == ["file=b"]

  def test_shouldRestoreFilesTheSameWayItMirroredThem(self, fixture):
    fileName = "inner-district"

    loc1Folder = fixture.loc1.mkdir("net")
    loc2Folder = fixture.loc2.mkdir("net")
    loc2File = loc2Folder.join(fileName)
    loc2File.write("")
    fixture.changeMTime(loc2File, 20)

    fixture.inter.restore("net", 1, anyUTCDateTime(), None, fixture.optsWith({
        "AdditionalSyncOpts": "--no-t"}))
    assert os.stat(str(loc1Folder / fileName)).st_mtime != 20

    fixture.inter.restore("net/" + fileName, 1, anyUTCDateTime(), 
        str(fixture.tmpdir), fixture.optsWith({}))
    assert os.stat(str(fixture.tmpdir / fileName)).st_mtime == 20
