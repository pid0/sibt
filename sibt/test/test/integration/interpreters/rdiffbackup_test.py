import time
import pytest
from test.common.assertutil import iterableContainsInAnyOrder
import os
from test.integration.interpreters.interpretertest import \
    InterpreterTestFixture, MirrorInterpreterTest, IncrementalInterpreterTest

class Fixture(InterpreterTestFixture):
  def __init__(self, tmpdir):
    self.load("rdiff-backup", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_RdiffBackupTest(MirrorInterpreterTest, IncrementalInterpreterTest):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 1

  def test_shouldUseRemoveOlderThanFeatureAfterSyncingIfSpecified(self, 
      fixture):
    assert "RemoveOlderThan" in fixture.inter.availableOptions
    assert "AdditionalSyncOpts" in fixture.inter.availableOptions

    def withTime(unixTime, andAlso=dict()):
      in2037 = aDay * 366 * 67
      andAlso["AdditionalSyncOpts"] = "--current-time=" + str(in2037 + unixTime)
      return fixture.optsWith(andAlso)

    firstFile = fixture.loc1.join("first")
    secondFile = fixture.loc1.join("second")
    thirdFile = fixture.loc1.join("third")

    aDay = 86400

    firstFile.write("")
    fixture.inter.sync(withTime(0))
    firstFile.remove()

    secondFile.write("")
    fixture.inter.sync(withTime(1 * aDay))

    thirdFile.write("")
    fixture.inter.sync(withTime(2 * aDay + 1, 
        andAlso={"RemoveOlderThan": "2D"}))

    files = os.listdir(str(fixture.loc2)) 
    assert "first" not in files
    assert "second" in files
    assert "third" in files

  def test_shouldReturn2IfAskedForTheLocationsItWritesTo(self, fixture):
    assert fixture.inter.writeLocIndices == [2]


