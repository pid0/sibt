import os.path
import time
import pytest
from test.common.assertutil import iterToTest, strToTest
import os
from test.integration.synchronizers import loadSynchronizer
from sibt.infrastructure.exceptions import ExternalFailureException
from test.common import relativeToProjectRoot
from test.common.builders import writeFileTree, remoteLocation, localLocation
from test.common import sshserver

def makeNonEmptyDir(container, name, innerFileName="file"):
  ret = container.mkdir(name)
  (container / name / innerFileName).write("")
  return ret

def sshLocationFromPath(path):
  return remoteLocation(protocol="ssh", login="", host="localhost",
      port=str(sshserver.Port), path=path)

class SynchronizerTestFixture(object):
  def __init__(self, tmpdir, location1FromPathFunc=localLocation, 
      location2FromPathFunc=localLocation,
      restoreLocFromPathFunc=localLocation):
    self.location1FromPath = location1FromPathFunc
    self.location2FromPath = location2FromPathFunc
    self.restoreLocFromPath = restoreLocFromPathFunc
    self.tmpdir = tmpdir

  def load(self, synchronizerName):
    path = relativeToProjectRoot("sibt/synchronizers/" + synchronizerName)
    self.syncer = loadSynchronizer(path)

    self.loc1 = self.tmpdir.mkdir("Loc $1\"\\'")
    self.loc2 = self.tmpdir.mkdir("Loc $2\"\\'")

  def optsWith(self, options):
    assert not str(self.loc1).endswith("/")
    options["Loc1"] = self.location1FromPath(str(self.loc1))
    options["Loc2"] = self.location2FromPath(str(self.loc2))
    return options

  def restorePort1File(self, fileName, version, dest, additionalOptions=dict()):
    options = self.optsWith(additionalOptions)
    self.syncer.restore(fileName, 1, version, 
        None if dest is None else self.restoreLocFromPath(str(dest)), options)

  def versionsOf(self, fileName, portNumber, additionalOptions=dict()):
    return self.syncer.versionsOf(fileName, portNumber, 
        self.optsWith(additionalOptions))

  @property
  def optionNames(self):
    return [optInfo.name for optInfo in self.syncer.availableOptions]

  def sync(self, additionalOptions=dict()):
    self.syncer.sync(self.optsWith(additionalOptions))
  def check(self, additionalOptions=dict()):
    return self.syncer.check(self.optsWith(additionalOptions))

  def changeMTime(self, path, newModiticationTime):
    os.utime(str(path), (0, newModiticationTime))

class SSHSupportingSyncerFixture(SynchronizerTestFixture):
  def __init__(self, tmpdir, sshServerSetup, location1FromPathFunc, 
      location2FromPathFunc, restoreLocFromPathFunc):
    super().__init__(tmpdir, location1FromPathFunc, location2FromPathFunc,
        restoreLocFromPathFunc)
    self.sshServerSetup = sshServerSetup

  def optsWith(self, options):
    if not "RemoteShellCommand" in options:
      options = dict(options)
      options["RemoteShellCommand"] = ("ssh -o UserKnownHostsFile={0} "
          "-i {1}").format(self.sshServerSetup.knownHostsFile,
              self.sshServerSetup.clientIdFile)
    return super().optsWith(options)


class SynchronizerTest(object):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 0
  @property
  def supportsNewlinesInFileNames(self):
    return True
  @property
  def supportsRecursiveCopying(self):
    return True

  @property
  def fileNameWithNewline(self):
    return "fi\nle1" if self.supportsNewlinesInFileNames else "file1"


  def getSingleVersion(self, fixture, additionalOptions=dict()):
    options = fixture.optsWith(additionalOptions)
    fixture.syncer.sync(options)
    versions = fixture.syncer.versionsOf(".", 1, options)
    assert len(versions) == 1
    return versions[0]

  def setUpTestTreeSyncAndDeleteIt(self, fixture, fileName1, options):
    writeFileTree(fixture.loc1,
        ["[folder],",
          fileName1,
          ".file2",
          ["sub",
            "file3 -> /home"]])

    fixture.syncer.sync(options)
    fixture.loc1.join("[folder],").remove()
    return fixture.syncer.versionsOf("[folder],", 1, options)[0]

  def test_shouldBeAbleToListDirsInLoc1AsTheyWereInThePastWithoutRecursion(
      self, fixture):
    options = fixture.optsWith(dict())

    version = self.setUpTestTreeSyncAndDeleteIt(fixture, 
        self.fileNameWithNewline, options)

    iterToTest(fixture.syncer.listFiles(
      "[folder],", 1, version, False, options)).shouldContainInAnyOrder(
        self.fileNameWithNewline, ".file2", "sub/")

    assert list(fixture.syncer.listFiles("[folder],/" + 
      self.fileNameWithNewline, 1, version, False, options)) == \
          [self.fileNameWithNewline]

    assert list(fixture.syncer.listFiles(".", 1, version, False, options)) == \
        ["[folder],/"]

    assert list(fixture.syncer.listFiles(".", 2, version, False, options)) == []

  def test_shouldBeAbleToGiveARecursiveFileListing(self, fixture):
    options = fixture.optsWith(dict())

    linkToLoc = fixture.tmpdir / "link-to-loc"
    linkToLoc.mksymlinkto(fixture.loc2)
    fixture.loc2 = linkToLoc
    version = self.setUpTestTreeSyncAndDeleteIt(fixture, 
        self.fileNameWithNewline, options)

    recursively = True

    iterToTest(fixture.syncer.listFiles(".", 1, version, 
      recursively, options)).shouldContainInAnyOrder(
        "[folder],/",
        "[folder],/" + self.fileNameWithNewline,
        "[folder],/.file2",
        "[folder],/sub/",
        "[folder],/sub/file3")

    iterToTest(fixture.syncer.listFiles("[folder],", 1, 
      version, recursively, options)).shouldContainInAnyOrder(
        self.fileNameWithNewline,
        ".file2",
        "sub/",
        "sub/file3")

    assert list(fixture.syncer.listFiles("[folder],/sub/file3", 1,
      version, recursively, options)) == ["file3"]

  def runFileRestoreTest(self, fixture, mTime, testFileName, testFunc):
    testFile = fixture.loc1 / testFileName
    testFile.write("foo")
    fixture.changeMTime(testFile, mTime)

    version = self.getSingleVersion(fixture)

    def checkRestoredFile(dest, pathToRestoredFile):
      fixture.restorePort1File(testFileName, version, dest)
      restoredFile = dest / pathToRestoredFile if dest is not None else \
          pathToRestoredFile
      assert restoredFile.read() == "foo"
      assert os.stat(str(restoredFile)).st_mtime == mTime

    testFunc(checkRestoredFile, testFile)

  def runFoldersRestoreTest(self, fixture, mTime, testFolderName, testFunc):
    testFolder = fixture.loc1.mkdir(testFolderName)
    (testFolder / "innocent-games").write("foo")
    fixture.changeMTime(testFolder, mTime)

    version = self.getSingleVersion(fixture)

    def checkRestoredFolder(dest, pathToRestoredFolder, 
        relativePathOfFileToRestore=None, ignoreAdditionalFiles=False):
      fixture.restorePort1File(testFolderName if \
          relativePathOfFileToRestore is None else relativePathOfFileToRestore, 
          version, dest)
      restored = dest / pathToRestoredFolder if dest is not None else\
          pathToRestoredFolder
      if not ignoreAdditionalFiles:
        assert len(os.listdir(str(restored))) == 1
      assert (restored / "innocent-games").read() == "foo"
      assert os.stat(str(restored)).st_mtime == mTime

    testFunc(checkRestoredFolder, testFolder)

  def test_shouldWriteOverExistingFilesAndIntoFoldersLikeCpWhenRestoringNonDirs(
      self, fixture, capfd):
    testFileName = "inner-district"
    def test(checkRestoredFile, _):
      existingFile = fixture.tmpdir / "existing-file"
      existingFile.write("")

      folder = fixture.tmpdir.mkdir("folder")
      makeNonEmptyDir(folder, testFileName)

      (fixture.tmpdir / testFileName).write("bar")
      checkRestoredFile(fixture.tmpdir, testFileName) 
      checkRestoredFile(fixture.tmpdir / "new-file", "") 
      checkRestoredFile(existingFile, "") 

      with pytest.raises(ExternalFailureException):
        checkRestoredFile(folder, "")
      _, stderr = capfd.readouterr()
      strToTest(stderr).shouldInclude("could not make way", testFileName)

    self.runFileRestoreTest(fixture, 20, testFileName, test)

  def test_shouldHandleSymlinksWithinLocsAsNonDirs(self, fixture):
    folder = fixture.tmpdir.mkdir("folder")
    (fixture.loc1 / "foo").mksymlinkto(folder)

    version = self.getSingleVersion(fixture)
    fixture.restorePort1File("foo", version, fixture.tmpdir / "restored")
    assert (fixture.tmpdir / "restored").readlink() == str(folder)

  def test_shouldWriteIntoDirsMergingContentLikeCpWhenRestoringFolders(
      self, fixture, capfd):
    testFolderName = "novels"

    def test(checkRestoredFolder, _):
      existingFile = fixture.tmpdir / "file"
      existingFile.write("")

      makeNonEmptyDir(fixture.tmpdir, testFolderName, innerFileName="inner")
      checkRestoredFolder(fixture.tmpdir, testFolderName,
          ignoreAdditionalFiles=True)
      if self.supportsRecursiveCopying:
        assert "inner" in os.listdir(str(fixture.tmpdir / testFolderName))

      with pytest.raises(ExternalFailureException):
        checkRestoredFolder(existingFile, "")
      _, stderr = capfd.readouterr()
      strToTest(stderr).shouldInclude("destination must be a directory")

      folderContainingFile = makeNonEmptyDir(fixture.tmpdir, "folder",
          innerFileName=testFolderName)
      linkToFolderContainingFile = fixture.tmpdir / "link1"
      linkToFolderContainingFile.mksymlinkto(folderContainingFile)
      with pytest.raises(ExternalFailureException):
        checkRestoredFolder(linkToFolderContainingFile, testFolderName)
      _, stderr = capfd.readouterr()
      strToTest(stderr).shouldInclude("contains non-directory", "not make way")

      checkRestoredFolder(fixture.tmpdir / "new", "")

      linkedFolder = fixture.tmpdir.mkdir("linked-folder")
      link = fixture.tmpdir / "link2"
      link.mksymlinkto(linkedFolder)
      checkRestoredFolder(link, testFolderName)
      assert link.islink()

    self.runFoldersRestoreTest(fixture, 100, testFolderName, test)

  def test_shouldEntirelyReplaceFileInSourceTreeWithANonDir(self, fixture):
    testFileName = "foo"

    def test(checkFunc, testFile):
      def checkRestoredFile():
        checkFunc(None, testFile)

      testFile.write("bar")
      checkRestoredFile() 

      testFile.remove()
      testFile.mkdir()
      (testFile / testFileName).write("")
      checkRestoredFile() 

    self.runFileRestoreTest(fixture, 150, testFileName, test)

  def test_shouldEntirelyReplaceAnyFileInTheSourceTreeWhenRestoringADir(self, 
      fixture):
    testFolderName = "baz"

    def test(checkFunc, testFolder):
      def checkRestoredFolder():
        checkFunc(None, testFolder, ignoreAdditionalFiles=False)

      testFolder.listdir()[0].write("something else")
      (testFolder / "another-file").write("")
      checkRestoredFolder()

      testFolder.remove()
      testFolder.write("a non-dir!")
      checkRestoredFolder()

      testFolder.remove()
      testFolder.mksymlinkto(fixture.loc1)
      checkRestoredFolder()
      assert not testFolder.islink()

      fixture.loc1.remove()
      checkFunc(None, testFolder, relativePathOfFileToRestore=".")
      assert testFolder in fixture.loc1.listdir()

    self.runFoldersRestoreTest(fixture, 423, testFolderName, test)

class MirrorSynchronizerTest(SynchronizerTest):
  def test_shouldMirrorLoc1InRepoAtLoc2WhenToldToSync(self, fixture):
    content = "... the raven “Nevermore.”"
    fixture.loc1.join("poe").write(content)
    folder = fixture.loc1.mkdir("folder")
    folder.join("file").write("")

    options = fixture.optsWith(dict())

    toBeRemoved = folder.join("to-be-removed")
    toBeRemoved.write("")
    fixture.syncer.sync(options)

    time.sleep(self.minimumDelayBetweenTestsInS)
    toBeRemoved.remove()
    fixture.syncer.sync(options)

    assert os.listdir(str(fixture.loc2 / "folder")) == ["file"]
    assert fixture.loc2.join("poe").read() == content

class IncrementalSynchronizerTest(SynchronizerTest):
  def getOlderVersionFromTwoSyncs(self, fixture, doBetweenSyncs=lambda: None,
      additionalOptions=dict()):
    options = fixture.optsWith(additionalOptions)

    fixture.syncer.sync(options)
    time.sleep(self.minimumDelayBetweenTestsInS)

    doBetweenSyncs()
    fixture.syncer.sync(options)

    versions = fixture.syncer.versionsOf(".", 1, options)

    return sorted(versions)[0]

  def test_shouldUseTheIncrementsAsVersions(self, fixture):
    topFile, folder, fileCreatedLater = writeFileTree(fixture.loc1,
        [".",
          "top [1]",
          ["poe [2]",
            "quote",
            "created-later [3]"]])

    fileCreatedLater.remove()
    topFile.write("old")

    older = self.getOlderVersionFromTwoSyncs(fixture, 
        doBetweenSyncs=lambda: (
          fileCreatedLater.write(""),
          topFile.write("new")))

    assert len(fixture.versionsOf("poe", 1)) == 2
    assert fixture.versionsOf("poe", 2) == []
    assert fixture.versionsOf("not-there", 1) == []
    assert len(fixture.versionsOf("poe/created-later", "1")) == 1

    fixture.restorePort1File("poe", older, None)
    assert os.listdir(str(folder)) == ["quote"]

    assert topFile.read() == "new"
    fixture.restorePort1File("top", older, None)
    assert topFile.read() == "old"

class UnidirectionalAugmentedPortSyncerTest(SynchronizerTest):
  def test_shouldSupportAnSSHLocationAtOneOfTheTwoPorts(self, fixture):
    assert "RemoteShellCommand" in fixture.optionNames

    iterToTest(fixture.syncer.ports).shouldContainMatching(
        lambda port: "ssh" in port.supportedProtocols,
        lambda port: "ssh" in port.supportedProtocols)

  def test_shouldWriteToPort2(self, fixture):
    assert fixture.syncer.ports[1].isWrittenTo

