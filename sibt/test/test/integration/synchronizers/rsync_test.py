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
  (localLocation, localLocation, localLocation),])
#  (sshLocationFromPath, localLocation, localLocation),
#  (localLocation, sshLocationFromPath, localLocation)])
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

    options = dict(AdditionalSyncOpts="$(echo --update)",
        AdditionalOptsBothWays="--exclude '*.o'")

    codeFile, binFile = writeFileTree(fixture.loc1, [".",
      ["src",
        "main.c [1]",
        "main.o [2]"]])
    fixture.changeMTime(codeFile, 20)
    codeFileBackup = fixture.loc2 / "src" / "main.c"
    binFileInBackup = fixture.loc2 / "src" / "main.o"

    fixture.sync(options)
    codeFileBackup.ensure(file=True)
    assert not os.path.isfile(str(binFileInBackup))
    codeFileBackup.write("//foo")
    fixture.changeMTime(codeFileBackup, 40)
    fixture.sync(options)
    binFileInBackup.write("ELF")

    codeFile.write("//bar")
    fixture.changeMTime(codeFileBackup, 60)
    fixture.restorePort1File(".", anyUTCDateTime(), None, options)
    assert codeFile.read() == "//foo"
    assert binFile.read() == ""

  def test_shouldProvideOptionToCompletelyIgnoreCertainDirs(self, fixture):
    assert "ExcludedDirs" in fixture.optionNames

    backupDir, realFile, tempFile = writeFileTree(fixture.loc1, [".",
      ["mnt",
        ["hdd* .",
          ["backup [1]"],
          ["data", "file [2]"]]],
      ["proc", 
        ["proc", ["1", ["attr", "foo"]]],
        ["1",
          ["attr", "exec [3]"]]]])
    fixture.loc2 = backupDir
    tempFile.remove()

    options = dict(ExcludedDirs="'/./mnt///./hdd* ./backup/' /proc/1/attr")
    fixture.sync(options)
    fixture.sync(options)

    assert "attr" not in os.listdir(str(backupDir / "proc" / "1"))
    assert "backup" not in os.listdir(str(backupDir / "mnt" / "hdd* ."))

    tempFile.write("foo")
    realFile.write("foo")
    fixture.restorePort1File(".", anyUTCDateTime(), None, options)
    fixture.restorePort1File("mnt/hdd* .", anyUTCDateTime(), None, options)
    fixture.restorePort1File("proc/1", anyUTCDateTime(), None, options)
    assert tempFile.read() == "foo"
    assert realFile.read() == ""

    destDir = fixture.tmpdir / "dest"
    fixture.restorePort1File("proc", anyUTCDateTime(), destDir, options)
    assert os.path.isfile(str(destDir / "proc" / "1" / "attr" / "foo"))
    assert not os.path.isfile(str(destDir / "1" / "attr" / "exec"))

  #shouldCheckIfResultingRsyncCommandHasValidSyntax <- AdditionalOpts, 
  #  ExcludedDirs; show error; also rdiff-backup

  def test_shouldAcknowledgeThatItDoesntSupportTwoSSHLocsAtATime(self, fixture):
    assert fixture.syncer.onePortMustHaveFileProtocol

