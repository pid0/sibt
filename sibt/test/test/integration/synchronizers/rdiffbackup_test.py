import time
import pytest
from test.common.assertutil import iterToTest
import os
from test.integration.synchronizers.synchronizertest import \
    SynchronizerTestFixture, MirrorSynchronizerTest, IncrementalSynchronizerTest

class Fixture(SynchronizerTestFixture):
  def __init__(self, tmpdir):
    self.load("rdiff-backup", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_RdiffBackupTest(MirrorSynchronizerTest, IncrementalSynchronizerTest):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 1
  @property
  def supportsNewlinesInFileNames(self):
    return False
  @property
  def supportsRecursiveCopying(self):
    return False

  def test_shouldUseRemoveOlderThanFeatureAfterSyncingIfSpecified(self, 
      fixture):
    assert "RemoveOlderThan" in fixture.syncer.availableOptions
    assert "AdditionalSyncOpts" in fixture.syncer.availableOptions

    def withTime(unixTime, andAlso=dict()):
      in2037 = oneDay * 366 * 67
      andAlso["AdditionalSyncOpts"] = "--current-time=" + str(in2037 + unixTime)
      return fixture.optsWith(andAlso)

    firstFile = fixture.loc1.join("first")
    secondFile = fixture.loc1.join("second")
    thirdFile = fixture.loc1.join("third")

    oneDay = 86400

    firstFile.write("")
    fixture.syncer.sync(withTime(0))
    firstFile.remove()

    secondFile.write("")
    fixture.syncer.sync(withTime(1 * oneDay))

    thirdFile.write("")
    fixture.syncer.sync(withTime(2 * oneDay + 1, 
        andAlso={"RemoveOlderThan": "2D"}))

    files = os.listdir(str(fixture.loc2)) 
    assert "first" not in files
    assert "second" in files
    assert "third" in files

  def test_shouldAcknowledgeWritingToPort2(self, fixture):
    iterToTest(fixture.syncer.ports).shouldContainMatching(
        lambda port: port.isWrittenTo == False,
        lambda port: port.isWrittenTo == True)


