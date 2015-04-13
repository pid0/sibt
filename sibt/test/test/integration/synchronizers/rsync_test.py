import pytest
from test.integration.synchronizers.synchronizertest import \
    SynchronizerTestFixture, MirrorSynchronizerTest
import os
from datetime import datetime, timezone
from test.common.builders import anyUTCDateTime

class Fixture(SynchronizerTestFixture):
  def __init__(self, tmpdir):
    self.load("rsync", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_RsyncTest(MirrorSynchronizerTest):
  def test_shouldSimplyUseTheFilesModificationTimeAsVersion(self, fixture):
    someFile = fixture.loc1.join("file")
    someFile.write("")
    fixture.changeMTime(str(someFile), 23)
    options = fixture.optsWith(dict())

    fixture.syncer.sync(options)

    expectedVersion = datetime(1970, 1, 1, 0, 0, 23, tzinfo=timezone.utc)
    assert fixture.syncer.versionsOf("file", 1, options) == [expectedVersion]

    assert fixture.syncer.versionsOf("does-not-exist", 1, options) == []
    assert fixture.syncer.versionsOf("file", 2, options) == []

  def test_shouldSupportInsertingCustomRsyncOptionsWhenSyncing(self, fixture):
    assert "AdditionalSyncOpts" in fixture.syncer.availableOptions

    fixture.loc1.join("file=a").write("")
    fixture.loc1.join("file=b").write("")

    fixture.syncer.sync(fixture.optsWith({"AdditionalSyncOpts": 
        "--exclude *=a"}))

    assert os.listdir(str(fixture.loc2)) == ["file=b"]

  def test_shouldRestoreFilesTheSameWayItMirroredThem(self, fixture):
    fileName = "inner-district"

    loc1Folder = fixture.loc1.mkdir("net")
    loc2Folder = fixture.loc2.mkdir("net")
    loc2File = loc2Folder.join(fileName)

    loc2File.write("bar")
    fixture.changeMTime(loc2File, 20)

    fixture.syncer.restore("net", 1, anyUTCDateTime(), None, fixture.optsWith({
        "AdditionalSyncOpts": "--no-t"}))
    assert os.stat(str(loc1Folder / fileName)).st_mtime != 20
    assert (loc1Folder / fileName).read() == "bar"
