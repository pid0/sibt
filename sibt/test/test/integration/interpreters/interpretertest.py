import os.path
import time
import pytest
from sibt.domain.defaultvalueinterpreter import DefaultValueInterpreter
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.application.configrepo import createHashbangAwareProcessRunner
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from test.common.assertutil import iterableContainsInAnyOrder
import os

class InterpreterTestFixture(object):
  def load(self, interpreterName, tmpdir):
    processRunner = createHashbangAwareProcessRunner("sibt/runners",
        SynchronousProcessRunner())
    path = os.path.abspath("sibt/interpreters/" + interpreterName)
    self.inter = DefaultValueInterpreter(
        ExecutableFileRuleInterpreter(path, os.path.basename(path),
            processRunner))

    self.loc1 = tmpdir.mkdir("Loc1")
    self.loc2 = tmpdir.mkdir("Loc2")
    self.tmpdir = tmpdir

  def optsWith(self, options):
    options["Loc1"] = str(self.loc1)
    options["Loc2"] = str(self.loc2)
    return options

  def changeMTime(self, path, newModiticationTime):
    os.utime(str(path), (0, newModiticationTime))

class InterpreterTest(object):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 0

  def test_shouldBeAbleToListDirsInLoc1AsTheyWereInThePastWithoutRecursion(
      self, fixture, capfd):
    folder = fixture.loc1.mkdir("folder")
    folder.join("file1").write("")
    folder.join(".file2").write("")
    subFolder = folder.mkdir("sub")
    subFolder.join("file3").write("")
    options = fixture.optsWith(dict())

    fixture.inter.sync(options)
    folder.remove()

    version = fixture.inter.versionsOf("folder", 1, options)[0]
    fixture.inter.listFiles("folder", 1, version, options)

    stdout, _ = capfd.readouterr()

    assert iterableContainsInAnyOrder(stdout.split(os.linesep)[:-1],
        lambda line: line == "F file1",
        lambda line: line == "F .file2",
        lambda line: line == "D sub")

    fixture.inter.listFiles("folder/file1", 1, version, options)
    stdout, _ = capfd.readouterr()
    assert stdout == "F file1\n"


class MirrorInterpreterTest(InterpreterTest):
  def rewriteLoc1PathForMirrorTest(self, path):
    return path

  def test_shouldMirrorLoc1InRepoAtLoc2IfToldToSync(self, fixture):
    content = "... the raven “Nevermore.”"
    fixture.loc1.join("poe").write(content)
    folder = fixture.loc1.mkdir("folder")
    folder.join("file").write("")

    options = fixture.optsWith(dict())
    options["Loc1"] = self.rewriteLoc1PathForMirrorTest(options["Loc1"])

    toBeRemoved = folder.join("to-be-removed")
    toBeRemoved.write("")
    fixture.inter.sync(options)

    time.sleep(self.minimumDelayBetweenTestsInS)
    toBeRemoved.remove()
    fixture.inter.sync(options)

    assert os.listdir(str(fixture.loc2 / "folder")) == ["file"]
    assert fixture.loc2.join("poe").read() == content

class IncrementalInterpreterTest(InterpreterTest):
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

    time.sleep(self.minimumDelayBetweenTestsInS)
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

