import os.path
import time
import pytest
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.application.configrepo import createHashbangAwareProcessRunner
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from test.common.interceptingoutput import InterceptingOutput
from test.common.assertutil import iterableContainsInAnyOrder
import os

class Fixture(object):
  def __init__(self, tmpdir):
    processRunner = createHashbangAwareProcessRunner("sibt/runners",
        SynchronousProcessRunner())
    path = os.path.abspath("sibt/interpreters/rdiff-backup")
    self.inter = ExecutableFileRuleInterpreter(path, os.path.basename(path),
        processRunner)

    self.loc1 = tmpdir.mkdir("Loc1")
    self.loc2 = tmpdir.mkdir("Loc2")
    self.tmpdir = tmpdir

  def optsWith(self, options):
    options["Loc1"] = str(self.loc1)
    options["Loc2"] = str(self.loc2)
    return options

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldReturnItsSupportedOptionsIfAsked(fixture):
  for option in ["RemoveOlderThan", "AdditionalSyncOpts"]: 
    assert option in fixture.inter.availableOptions 

def test_shouldCopyLoc1ToRdiffRepoAtLoc2IfToldToSync(fixture):
  content = "... the raven “Nevermore.”"
  fixture.loc1.join("poe").write(content)

  fixture.inter.sync(fixture.optsWith(dict()))

  assert os.listdir(str(fixture.loc2)) == ["poe", "rdiff-backup-data"]
  assert fixture.loc2.join("poe").read() == content

def test_shouldUseRemoveOlderThanFeatureAfterSyncingIfSpecified(fixture):
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
  fixture.inter.sync(withTime(2 * aDay + 1, andAlso={"RemoveOlderThan": "2D"}))

  files = os.listdir(str(fixture.loc2)) 
  assert "first" not in files
  assert "second" in files
  assert "third" in files

def test_shouldUseTheIncrementsAsVersions(fixture):
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
  assert len(fixture.inter.versionsOf("poe/created-later", "1", 
      options)) == 1
  assert len(versions) == 2

  older = versions[0]
  newer = versions[1]
  if newer < older:
    older, newer = newer, older

  fixture.inter.restore("poe", 1, older, None, options)
  assert os.listdir(str(folder)) == ["quote"]
  assert quoteFile.read() == ravenQuote

  destFile = fixture.tmpdir.join("backup")
  fixture.inter.restore("top", 1, older, str(destFile), options)
  assert topFile.read() == "foo"
  assert destFile.read() == someContent

def test_shouldBeAbleToListDirectories(fixture):
  folder = fixture.loc1.mkdir("folder")
  folder.join("file1").write("")
  folder.join("file2").write("")
  folder.mkdir("sub")
  options = fixture.optsWith(dict())

  fixture.inter.sync(options)
  folder.remove()

  version = fixture.inter.versionsOf("folder", 1, options)[0]
  stdout = None
  with InterceptingOutput.stdout() as stdout:
    fixture.inter.listFiles("folder", 1, version, options)

  assert iterableContainsInAnyOrder(stdout.stringBuffer.split(os.linesep)[:-1],
      lambda line: line == "F file1",
      lambda line: line == "F file2",
      lambda line: line == "D sub")

  with InterceptingOutput.stdout() as stdout:
    fixture.inter.listFiles("folder/file1", 1, version, options)
  assert stdout.stringBuffer == "F file1\n"


