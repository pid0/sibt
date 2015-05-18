import pytest
from test.integration.synchronizers.synchronizertest import \
    SSHSupportingSyncerFixture, MirrorSynchronizerTest, sshLocationFromPath, \
    UnidirectionalAugmentedPortSyncerTest
import os
from datetime import datetime, timezone
from test.common.builders import anyUTCDateTime, localLocation, writeFileTree
from test.common.sshserver import sshServerFixture
from test.common.assertutil import iterToTest

class Fixture(SSHSupportingSyncerFixture):
  def __init__(self, tmpdir, sshServerSetup, location1FromPathFunc, 
      location2FromPathFunc, restoreLocFromPathFunc):
    super().__init__(tmpdir, sshServerSetup, location1FromPathFunc, 
      location2FromPathFunc, restoreLocFromPathFunc)
    self.load("rsync")

@pytest.fixture(params=[
  (sshLocationFromPath, localLocation, localLocation),
  (localLocation, sshLocationFromPath, localLocation)])
def fixture(request, tmpdir, sshServerFixture):
  loc1Func, loc2Func, restoreFunc = request.param
  return Fixture(tmpdir, sshServerFixture, loc1Func, loc2Func, restoreFunc)

class Test_RsyncTest(MirrorSynchronizerTest, 
    UnidirectionalAugmentedPortSyncerTest):
  def test_shouldRememberTheVersionTimestampInAFileAndElseFallBackOnTheMTime(
      self, fixture):
    someFile = fixture.loc1.join("file")
    someFile.write("")
    fixture.changeMTime(str(someFile), 23)
    options = fixture.optsWith(dict())

    fixture.syncer.sync(options)

    assert fixture.syncer.versionsOf("does-not-exist", 1, options) == []
    assert fixture.syncer.versionsOf("file", 2, options) == []

    iterToTest(fixture.syncer.versionsOf("file", 1, options)).\
        shouldContainMatching(lambda version: version.year > 1970)

    (fixture.loc2 / ".sibt-rsync-timestamp").remove()
    fixture.syncer.versionsOf("file", 1, options) == \
        [datetime(1970, 1, 1, 0, 0, 23, tzinfo=timezone.utc)]

  def test_shouldTakeCustomOptionsForSyncingAndForSyncingAndRestoring(self, 
      fixture):
    assert "AdditionalSyncOpts" in fixture.optionNames
    assert "AdditionalOptsBothWays" in fixture.optionNames

    infoFile, = writeFileTree(fixture.loc1, [".",
      ["proc",
        "cpuinfo"],
      ["foo",
        ["proc",
          "cpuinfo [1]"]]])
    infoFile.write("blah")

    options = { "AdditionalSyncOpts": "--exclude '/?roc/cpu*'",
        "AdditionalOptsBothWays": "$(echo --no-t)" }

    fixture.sync(options)
    assert "cpuinfo" not in os.listdir(str(fixture.loc2 / "proc"))

    fixture.changeMTime(fixture.loc2 / "foo" / "proc" / "cpuinfo", 20)
    infoFile.remove()
    fixture.restorePort1File("foo/proc", anyUTCDateTime(), None, options)
    assert infoFile.read() == "blah"
    assert os.stat(str(infoFile)).st_mtime != 20

  def test_shouldAcknowledgeThatItDoesntSupportTwoSSHLocsAtATime(self, fixture):
    assert fixture.syncer.onePortMustHaveFileProtocol

