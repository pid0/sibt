import time
import pytest
from test.common.assertutil import iterableContainsInAnyOrder
import os
from test.integration.interpreters.interpretertest import \
    InterpreterTestFixture, MirrorInterpreterTest

class Fixture(InterpreterTestFixture):
  def __init__(self, tmpdir):
    self.load("rdiff-backup", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

class Test_RdiffBackupTest(MirrorInterpreterTest):
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

  def test_shouldUseTheIncrementsAsVersions(self, fixture):
    folder = fixture.loc1.mkdir("poe")
    topFile = fixture.loc1.join("top")
    quoteFile = folder.join("quote")
    fileLaterCreated = folder.join("created-later")

    options = fixture.optsWith(dict())

    ravenQuote = "tell me what thy lordly name is"
    someContent = "content"

    topFile.write(someContent)
    quoteFile.write(ravenQuote)
    fixture.inter.sync(options)

    time.sleep(1)
    fileLaterCreated.write("")
    topFile.write("foo")
    fixture.inter.sync(options)

    versions = fixture.inter.versionsOf("poe", 1, options)
    assert fixture.inter.versionsOf("poe", 2, options) == []
    assert fixture.inter.versionsOf("not-there", 1, options) == []
    assert len(fixture.inter.versionsOf("poe/created-later", "1", 
        options)) == 1
    assert len(versions) == 2

    older, newer = sorted(versions)

    fixture.inter.restore("poe", 1, older, None, options)
    assert os.listdir(str(folder)) == ["quote"]
    assert quoteFile.read() == ravenQuote

    destFile = fixture.tmpdir.join("backup")
    fixture.inter.restore("top", 1, older, str(destFile), options)
    assert topFile.read() == "foo"
    assert destFile.read() == someContent

  def test_shouldReturn2IfAskedForTheLocationsItWritesTo(self, fixture):
    assert fixture.inter.writeLocIndices == [2]


