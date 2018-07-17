import pytest
from test.integration.synchronizers.synchronizertest import \
    SSHSupportingSyncerFixture, MirrorSynchronizerTest, sshLocationFromPath, \
    UnidirectionalAugmentedPortSyncerTest, ExcludingSynchronizerTest
import os
from datetime import datetime, timezone
from test.common.builders import anyUTCDateTime, localLocation, writeFileTree
from test.common.sshserver import sshServerFixture
from test.common.assertutil import iterToTest, stringThat, strToTest
from test.common import relativeToProjectRoot
from test.integration.bashfunctestfixture import BashFuncTestFixture

class Fixture(SSHSupportingSyncerFixture):
  def __init__(self, tmpdir, sshServerSetup, location1FromPathFunc, 
      location2FromPathFunc, restoreLocFromPathFunc):
    super().__init__(tmpdir, sshServerSetup, location1FromPathFunc, 
      location2FromPathFunc, restoreLocFromPathFunc)
    self.load("rsync")

@pytest.fixture(params=[
  (sshLocationFromPath, localLocation, sshLocationFromPath),
  (localLocation, sshLocationFromPath, localLocation),
  (localLocation, localLocation, localLocation)
  ])
def fixture(request, tmpdir, sshServerFixture):
  loc1Func, loc2Func, restoreFunc = request.param
  return Fixture(tmpdir, sshServerFixture, loc1Func, loc2Func, restoreFunc)

class Test_RsyncTest(MirrorSynchronizerTest, 
    UnidirectionalAugmentedPortSyncerTest, ExcludingSynchronizerTest):
  def test_shouldRememberTheVersionTimestampInAFileAndElseFallBackOnTheMTime(
      self, fixture):
    someFile = fixture.loc1.join("file")
    someFile.write("")
    fixture.changeMTime(str(someFile), 23)

    fixture.sync()

    assert fixture.versionsOf("does-not-exist", 1) == []

    iterToTest(fixture.versionsOf("file", 1)).shouldContainMatching(
        lambda version: version.year > 1970)

    (fixture.loc2 / ".sibt-rsync-timestamp").remove()
    fixture.versionsOf("file", 1) == \
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

  def test_shouldFindSyntaxErrorsInItsOptions(self, fixture):
    assert fixture.check(dict(
      AdditionalSyncOpts="--one-file-system",
      ExcludedDirs="/foo")) == []

    iterToTest(fixture.check(dict(
      AdditionalSyncOpts="'", 
      AdditionalOptsBothWays="'", 
      RemoteShellCommand="("))).shouldContainMatchingInAnyOrder(
          stringThat.shouldInclude("unexpected", "AdditionalOptsBothWays"),
          stringThat.shouldInclude("unexpected", "AdditionalSyncOpts"),
          stringThat.shouldInclude("unexpected", "RemoteShellCommand"))

  def test_shouldBeAbleToDryTestTheRsyncCommandThatWouldBeUsedToSync(
      self, fixture):
    assert "DryRun" in fixture.optionNames

    iterToTest(fixture.check(dict(DryRun=True, AdditionalSyncOpts="--bar"))).\
        shouldContainMatching(stringThat.shouldInclude("unknown option", "bar"))

    (fixture.loc1 / "file").write("")
    assert fixture.check({}) == []
    assert not os.path.isfile(str(fixture.loc2 / "file"))

    fixture.loc1.chmod(0o300)
    iterToTest(fixture.check(dict(DryRun=True))).shouldContainMatching(
      stringThat.shouldInclude("Permission denied"))
    assert fixture.check(dict(DryRun=False)) == []

  def test_shouldAcknowledgeThatItDoesntSupportTwoSSHLocsAtATime(self, fixture):
    assert fixture.syncer.onePortMustHaveFileProtocol

@pytest.fixture
def funcFixture():
  return BashFuncTestFixture(relativeToProjectRoot(
    "sibt/synchronizers/rsync"))

class Test_RsyncFunctionsTest(object):
  def test_shouldCorrectlyReanchorExcludedDirs(self, funcFixture):
    assert funcFixture.compute("""
      source '{0}' /dev/null ''
      declare -a ExcludedDirs=(/mnt/data)
      declare -a result=()
      -get-reanchored-exclude-opts mnt 1 result
      echo -n "${result[1]}" """.replace("{0}",
        relativeToProjectRoot("sibt/runners/bash-runner"))) == b"/data/"
