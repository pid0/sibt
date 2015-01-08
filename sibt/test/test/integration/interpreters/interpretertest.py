import os.path
import time
import pytest
from test.common.assertutil import iterableContainsInAnyOrder, equalsPred
import os
from test.integration.interpreters import loadInterpreter

class InterpreterTestFixture(object):
  def load(self, interpreterName, tmpdir):
    path = os.path.abspath("sibt/interpreters/" + interpreterName)
    self.inter = loadInterpreter(path)

    self.loc1 = tmpdir.mkdir("Loc1")
    self.loc2 = tmpdir.mkdir("Loc2")
    self.tmpdir = tmpdir

  def optsWith(self, options):
    options["Loc1"] = str(self.loc1)
    assert not options["Loc1"].endswith("/")
    options["Loc2"] = str(self.loc2)
    return options

  def changeMTime(self, path, newModiticationTime):
    os.utime(str(path), (0, newModiticationTime))

class InterpreterTest(object):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 0
  @property
  def supportsNewlinesInFileNames(self):
    return True
  @property
  def fileNameWithNewline(self):
    return "fi\nle1" if self.supportsNewlinesInFileNames else "file1"

  def writeFileTree(self, folder, fileList):
    newFolder = folder.mkdir(fileList[0])
    for subFile in fileList[1:]:
      if isinstance(subFile, list):
        self.writeFileTree(newFolder, subFile)
      elif " -> " in subFile:
        symlinkName, symlinkDest = subFile.split(" -> ")
        newFolder.join(symlinkName).mksymlinkto(symlinkDest)
      else:
        newFolder.join(subFile).write("")

  def setUpTestTreeSyncAndDeleteIt(self, fixture, fileName1, options):
    self.writeFileTree(fixture.loc1,
        ["[folder],",
          fileName1,
          ".file2",
          ["sub",
            "file3 -> /home"]])

    fixture.inter.sync(options)
    fixture.loc1.join("[folder],").remove()
    return fixture.inter.versionsOf("[folder],", 1, options)[0]

  def test_shouldBeAbleToListDirsInLoc1AsTheyWereInThePastWithoutRecursion(
      self, fixture):
    options = fixture.optsWith(dict())

    version = self.setUpTestTreeSyncAndDeleteIt(fixture, 
        self.fileNameWithNewline, options)

    assert iterableContainsInAnyOrder(
        fixture.inter.listFiles("[folder],", 1, version, False, options), 
        *map(equalsPred, [self.fileNameWithNewline, ".file2", "sub/"]))

    assert list(fixture.inter.listFiles("[folder],/" + 
      self.fileNameWithNewline, 1, version, False, options)) == \
          [self.fileNameWithNewline]

    assert list(fixture.inter.listFiles(".", 1, version, False, options)) == \
        ["[folder],/"]

    assert list(fixture.inter.listFiles(".", 2, version, False, options)) == []

  def test_shouldBeAbleToGiveARecursiveFileListing(self, fixture):
    options = fixture.optsWith(dict())

    version = self.setUpTestTreeSyncAndDeleteIt(fixture, 
        self.fileNameWithNewline, options)

    recursively = True

    assert iterableContainsInAnyOrder(fixture.inter.listFiles(".", 1, version, 
      recursively, options), *map(equalsPred, [
        "[folder],/",
        "[folder],/" + self.fileNameWithNewline,
        "[folder],/.file2",
        "[folder],/sub/",
        "[folder],/sub/file3"]))

    assert iterableContainsInAnyOrder(fixture.inter.listFiles("[folder],", 1, 
      version, recursively, options), *map(equalsPred, [
        self.fileNameWithNewline,
        ".file2",
        "sub/",
        "sub/file3"]))

    assert list(fixture.inter.listFiles("[folder],/sub/file3", 1,
      version, recursively, options)) == ["file3"]

class MirrorInterpreterTest(InterpreterTest):
  def rewriteLoc1PathForMirrorTest(self, path):
    return path

  def test_shouldMirrorLoc1InRepoAtLoc2WhenToldToSync(self, fixture):
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

