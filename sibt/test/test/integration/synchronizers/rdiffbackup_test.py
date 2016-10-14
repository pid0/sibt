import pytest
from datetime import timedelta
from test.common.assertutil import iterToTest, stringThat
import os
from test.integration.synchronizers.synchronizertest import \
    SSHSupportingSyncerFixture, MirrorSynchronizerTest, \
    IncrementalSynchronizerTest, UnidirectionalAugmentedPortSyncerTest, \
    sshLocationFromPath
from test.integration.bashfunctestfixture import BashFuncTestFixture
from test.common.builders import localLocation
from test.common.sshserver import sshServerFixture
from test.common import relativeToProjectRoot

class Fixture(SSHSupportingSyncerFixture):
  def __init__(self, tmpdir, sshServerSetup, location1FromPathFunc,
      location2FromPathFunc, restoreLocFromPathFunc):
    super().__init__(tmpdir, sshServerSetup, location1FromPathFunc, 
        location2FromPathFunc, restoreLocFromPathFunc)
    self.load("rdiff-backup")

@pytest.fixture(params=[
  (sshLocationFromPath, sshLocationFromPath, sshLocationFromPath),
  (localLocation, localLocation, localLocation)
  ])
def fixture(request, tmpdir, sshServerFixture):
  loc1Func, loc2Func, restoreFunc = request.param
  return Fixture(tmpdir, sshServerFixture, loc1Func, loc2Func, restoreFunc)

class Test_RdiffBackupTest(MirrorSynchronizerTest, IncrementalSynchronizerTest,
    UnidirectionalAugmentedPortSyncerTest):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 1
  @property
  def supportsNewlinesInFileNames(self):
    return False
  @property
  def supportsRecursiveCopying(self):
    return False
  @property
  def canWriteToSymlinkedLoc(self):
    return False

  def test_shouldUseRemoveOlderThanFeatureAfterSyncingIfSpecified(self, 
      fixture):
    assert "RemoveOlderThan" in fixture.optionNames
    assert "AdditionalSyncOpts" in fixture.optionNames

    def withTime(unixTime, andAlso=dict()):
      in2037 = oneDay * 366 * 67
      andAlso["AdditionalSyncOpts"] = "--current-time=" + str(in2037 + unixTime)
      return andAlso

    firstFile = fixture.loc1.join("first")
    secondFile = fixture.loc1.join("second")
    thirdFile = fixture.loc1.join("third")

    oneDay = 86400

    firstFile.write("")
    fixture.sync(withTime(0))
    firstFile.remove()

    secondFile.write("foo")
    fixture.sync(withTime(1 * oneDay))

    latestTime = 2 * oneDay + 1
    secondFile.write("quux")
    thirdFile.write("")
    fixture.sync(withTime(latestTime,
        andAlso={"RemoveOlderThan": timedelta(days=2)}))

    assert len(fixture.versionsOf("first", 1, withTime(latestTime))) == 0
    assert len(fixture.versionsOf("second", 1, 
      withTime(latestTime))) == 2
    assert len(fixture.versionsOf("third", 1, withTime(latestTime))) == 1

  def test_shouldAcknowledgeWritingToPort2(self, fixture):
    iterToTest(fixture.syncer.ports).shouldContainMatching(
        lambda port: port.isWrittenTo == False,
        lambda port: port.isWrittenTo == True)

  def test_shouldFindSyntaxErrorsInItsOptions(self, fixture):
    assert fixture.check(dict(
      AdditionalSyncOpts="--exclude '**/.*'")) == []

    iterToTest(fixture.check(dict(
      AdditionalSyncOpts="--exclude '",
      RemoteShellCommand="("))).shouldContainMatchingInAnyOrder(
          stringThat.shouldInclude("AdditionalSyncOpts", "unexpected"),
          stringThat.shouldInclude("RemoteShellCommand", "unexpected"))


@pytest.fixture
def funcFixture():
  return BashFuncTestFixture(relativeToProjectRoot(
    "sibt/synchronizers/rdiff-backup"))

class Test_FileTypeTestFunctionTest(object):
  def test_shouldChooseTheMinimumVersionLaterThanTheSpecifiedOne(
      self, funcFixture):
    assert funcFixture.compute(r"""
      { echo '0 directory'
        echo '10 regular'
        echo '20 directory'; } | -parse-repo-file-type 9""") == b"regular\n"
