import os.path
import time
import pytest
from test.common.assertutil import iterToTest, strToTest, stringThat
import os
from test.integration.synchronizers import loadSynchronizer
from sibt.infrastructure.exceptions import ExternalFailureException
from test.common import relativeToProjectRoot
from test.common.builders import writeFileTree, remoteLocation, localLocation, \
    mkSyncerOpts
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
    return mkSyncerOpts(**options)

  def restorePort1File(self, fileName, version, dest, additionalOptions=dict()):
    options = self.optsWith(additionalOptions)
    self.syncer.restore(options, fileName, 1, version, 
        None if dest is None else self.restoreLocFromPath(str(dest)))

  def listFiles(self, relativePath, version, portNumber=1, recursively=True):
    ret = []
    def visitorFunc(fileName):
      ret.append(fileName)
    self.syncer.listFiles(self.optsWith(dict()), visitorFunc,
        relativePath, portNumber, version, recursively)
    return ret
  def listPort1Files(self, *args, **kwargs):
    return self.listFiles(*args, **kwargs, portNumber=1)
  def listPort2Files(self, *args, **kwargs):
    return self.listFiles(*args, **kwargs, portNumber=2)

  def versionsOf(self, fileName, portNumber, additionalOptions=dict()):
    return self.syncer.versionsOf(self.optsWith(additionalOptions), 
        fileName, portNumber)


  def syncAndGetVersions(self, additionalOptions=dict()):
    self.sync(additionalOptions)
    return self.versionsOf(".", 1, additionalOptions)
  def getSingleVersion(self, additionalOptions=dict()):
    versions = self.syncAndGetVersions(additionalOptions)
    assert len(versions) == 1
    return versions[0]
  def syncAndGetLatestVersion(self, additionalOptions=dict()):
    return max(self.syncAndGetVersions(additionalOptions))

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
      options["RemoteShellCommand"] = self.sshServerSetup.remoteShellCommand
    return super().optsWith(options)


class ListingSynchronizerTest(object):
  @property
  def supportsNewlinesInFileNames(self):
    return True
  @property
  def canWriteToSymlinkedLoc(self):
    return True

  @property
  def fileNameWithNewline(self):
    return "fi\nl\\e1" if self.supportsNewlinesInFileNames else "fil\\e1"

  def setUpTestTreeSyncAndDeleteIt(self, fixture, fileName1, options):
    writeFileTree(fixture.loc1,
        ["[folder],",
          fileName1,
          ".file2",
          ["sub",
            "file3 -> /usr"]])

    fixture.sync(options)
    fixture.loc1.join("[folder],").remove()
    return fixture.versionsOf("[folder],", 1, options)[0]

  def test_shouldBeAbleToListDirsInLoc1AsTheyWereInThePastWithoutRecursion(
      self, fixture):
    version = self.setUpTestTreeSyncAndDeleteIt(fixture, 
        self.fileNameWithNewline, dict())

    iterToTest(fixture.listPort1Files(
      "[folder],", version, recursively=False)).shouldContainInAnyOrder(
        self.fileNameWithNewline, ".file2", "sub/")

    assert fixture.listPort1Files("[folder],/" + 
      self.fileNameWithNewline, version, recursively=False) == \
          [self.fileNameWithNewline]

    assert fixture.listPort1Files(".", version, recursively=False) == \
        ["[folder],/"]

    assert fixture.listPort2Files(".", version, recursively=False) == []

  def test_shouldBeAbleToGiveARecursiveFileListing(self, fixture):
    if self.canWriteToSymlinkedLoc:
      linkToLoc = fixture.tmpdir / "link-to-loc"
      linkToLoc.mksymlinkto(fixture.loc2)
      fixture.loc2 = linkToLoc
    version = self.setUpTestTreeSyncAndDeleteIt(fixture, 
        self.fileNameWithNewline, dict())

    iterToTest(fixture.listPort1Files(".", version, 
      recursively=True)).shouldContainInAnyOrder(
        "[folder],/",
        "[folder],/" + self.fileNameWithNewline,
        "[folder],/.file2",
        "[folder],/sub/",
        "[folder],/sub/file3")

    iterToTest(fixture.listPort1Files("[folder],", version, 
      recursively=True)).shouldContainInAnyOrder(
        self.fileNameWithNewline,
        ".file2",
        "sub/",
        "sub/file3")

    assert list(fixture.listPort1Files("[folder],/sub/file3",
      version, recursively=True)) == ["file3"]

class RestoringSynchronizerTest(object):
  @property
  def minimumDelayBetweenTestsInS(self):
    return 0
  @property
  def supportsRecursiveCopying(self):
    return True

  def runFileRestoreTest(self, fixture, mTime, testFileName, testFunc):
    content = "file restore test content"
    testFile = fixture.loc1 / testFileName
    testFile.write(content)
    fixture.changeMTime(testFile, mTime)

    version = fixture.getSingleVersion()

    def checkRestoredFile(dest, pathToRestoredFile):
      fixture.restorePort1File(testFileName, version, dest)
      restoredFile = dest / pathToRestoredFile if dest is not None else \
          pathToRestoredFile
      assert restoredFile.read() == content
      assert os.stat(str(restoredFile)).st_mtime == mTime

    testFunc(checkRestoredFile, testFile)

  def runFoldersRestoreTest(self, fixture, mTime, testFolderName, testFunc):
    testFolder = fixture.loc1.mkdir(testFolderName)
    (testFolder / "innocent-games").write("foo")
    fixture.changeMTime(testFolder, mTime)

    version = fixture.getSingleVersion()

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
      checkRestoredFile(fixture.tmpdir / r"new-\2&\Lfile", "") 
      checkRestoredFile(existingFile, "") 

      with pytest.raises(ExternalFailureException):
        checkRestoredFile(folder, "")
      _, stderr = capfd.readouterr()
      strToTest(stderr).shouldInclude(testFileName)
      assert "could not make way" in stderr or "exists" in stderr

    self.runFileRestoreTest(fixture, 20, testFileName, test)

  def test_shouldTreatSymlinksWithinLocsAsNonDirs(self, fixture):
    folder = fixture.tmpdir.mkdir("folder")
    (fixture.loc1 / "foo").mksymlinkto(folder)

    version = fixture.getSingleVersion()
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
      strToTest(stderr).shouldIncludeAtLeastOneOf(
          "not a directory",
          "destination must be a directory")

      folderContainingFile = makeNonEmptyDir(fixture.tmpdir, "folder",
          innerFileName=testFolderName)
      linkToFolderContainingFile = fixture.tmpdir / "link1"
      linkToFolderContainingFile.mksymlinkto(folderContainingFile)
      with pytest.raises(ExternalFailureException):
        checkRestoredFolder(linkToFolderContainingFile, testFolderName)
      _, stderr = capfd.readouterr()
      strToTest(stderr).shouldIncludeAtLeastOneOf(
          "contains non-directory",
          "not a directory")

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

  def test_shouldBeAbleToRestoreFilesDeeperWithinALoc(self, fixture):
    testFile, = writeFileTree(fixture.loc1, ["a", ["b", ["c", "file [1]"]]])
    quote = "how the poor devils beat against the walls"
    testFile.write(quote)
    version = fixture.getSingleVersion()

    testFile.remove()
    fixture.restorePort1File("a/b/c/file", version, None)
    assert testFile.read() == quote

    destFile = fixture.tmpdir / "dest"
    fixture.restorePort1File("a/b/c/file", version, str(destFile))
    assert destFile.read() == quote

class SynchronizerTest(ListingSynchronizerTest, RestoringSynchronizerTest):
  pass


class ExcludingSynchronizerTest(SynchronizerTest):
  @property
  def isMirroring(self):
    return True

  def test_shouldProvideOptionToCompletelyIgnoreCertainDirs(self, fixture):
    assert "ExcludedDirs" in fixture.optionNames

    backupDir, realFile, tempFile = writeFileTree(fixture.loc1, [".",
      ["mnt",
        ["hdd* .",
          ["backup [1]"],
          ["data", "file [2]"]]],
      ["proc", 
        ["1",
          ["attr", "exec [3]"]]]])
    fixture.loc2 = backupDir

    options = dict(ExcludedDirs=
        "'/./mnt///./hdd* ./backup/' /proc/1/attr")
    fixture.sync(options)
    version = fixture.syncAndGetLatestVersion(options)

    assert len(fixture.versionsOf("mnt/hdd* ./backup", 1, options)) == 0
    assert len(fixture.versionsOf("proc/1/attr/exec", 1, options)) == 0

    if self.isMirroring:
      assert "attr" not in os.listdir(str(backupDir / "proc" / "1"))
      assert "backup" not in os.listdir(str(backupDir / "mnt" / "hdd* ."))

    tempFile.write("foo")
    realFile.write("foo")
    fixture.restorePort1File(".", version, None, options)
    fixture.restorePort1File("mnt/hdd* .", version, None, options)
    fixture.restorePort1File("proc/1", version, None, options)
    assert tempFile.read() == "foo"
    assert realFile.read() == ""

  def test_shouldNotUseExcludedDirPathsIfTheyCantBeReanchored(self, fixture):
    testFile, = writeFileTree(fixture.loc1, [".",
      ["mnt",
        ["data", 
          "file [1]"]]])
    
    options = dict(ExcludedDirs="/data")
    version = fixture.syncAndGetLatestVersion(options)

    testFile.write("bar")
    fixture.restorePort1File("mnt/data", version, None, options)
    assert testFile.read() == ""

  def test_shouldAnchorExcludeDirsCorrectlyRegardlessOfRestoreTarget(
      self, fixture):
    writeFileTree(fixture.loc1, [".",
      ["foo",
        ["bar"],
        ["foo",
          ["bar"]]]])

    options = dict(ExcludedDirs="/foo/bar")
    version = fixture.syncAndGetLatestVersion(options)

    destDir = fixture.tmpdir / "dest"
    fixture.restorePort1File("foo", version, destDir, options)
    assert os.path.isdir(str(destDir / "foo" / "bar"))
    assert not os.path.isdir(str(destDir / "bar"))

  def test_shouldIgnorePurelyStringBasedCommonPrefixesInExcludedDirsReanchoring(
      self, fixture):
    testFile, = writeFileTree(fixture.loc1, [".",
      ["foo",
        ["bar", "file [1]"]]])

    options = dict(ExcludedDirs="/foobar")
    version = fixture.syncAndGetLatestVersion(options)

    testFile.write("foo")
    fixture.restorePort1File("foo/bar", version, None, options)
    assert testFile.read() == ""

  def test_shouldIgnoreStringBasedPrefixesWhenGettingVersions(self, fixture):
    fixture.loc1.mkdir("foobar")
    options = dict(ExcludedDirs="/foo")
    fixture.sync(options)
    assert len(fixture.versionsOf("foobar", 1, options)) > 0

  def test_shouldFindSyntaxErrorsInTheExcludedDirsOption(self, fixture):
    assert fixture.check(dict(ExcludedDirs="'/foo bar'")) == []

    iterToTest(fixture.check(dict(ExcludedDirs="/foo'b"))).\
        shouldContainMatching(stringThat.shouldInclude(
          "unexpected", "ExcludedDirs"))

    iterToTest(fixture.check(dict(ExcludedDirs="relative/foo/bar"))).\
        shouldContainMatching(stringThat.shouldInclude("ExcludedDirs",
          "relative/foo/bar", "absolute"))
    iterToTest(fixture.check(dict(ExcludedDirs="'/foo' ''"))).\
        shouldContainMatching(stringThat.shouldInclude(
          "absolute", "ExcludedDirs"))

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
  def getTwoVersions(self, fixture, doBetweenSyncs=lambda: None,
      additionalOptions=dict()):
    fixture.sync(additionalOptions)
    time.sleep(self.minimumDelayBetweenTestsInS)

    doBetweenSyncs()
    fixture.sync(additionalOptions)

    versions = fixture.versionsOf(".", 1, additionalOptions)
    assert(len(versions)) == 2
   
    return versions

  def test_shouldUseTheIncrementsAsVersions(self, fixture):
    sameFile, topFile, folder, oldFile, newFile = writeFileTree(fixture.loc1,
        [".",
          "samefile [1]",
          "file [2]",
          ["usr [3]",
            "oldfile [4]",
            "newfile [5]"]])

    sameFile.write("same")
    newFile.remove()
    topFile.write("old")

    oldVersion, newVersion = self.getTwoVersions(fixture, 
        doBetweenSyncs=lambda: (
          topFile.write("new"),
          newFile.write(""),
          oldFile.remove()))

    assert len(fixture.versionsOf("usr", 1)) == 2
    assert fixture.versionsOf("usr", 2) == []
    assert fixture.versionsOf("not-there", 1) == []
    assert len(fixture.versionsOf("usr/newfile", "1")) == 1

    iterToTest(fixture.listPort1Files(".", oldVersion)).shouldContainInAnyOrder(
        "samefile", "file", "usr/", "usr/oldfile")
    iterToTest(fixture.listPort1Files(".", newVersion)).shouldContainInAnyOrder(
        "samefile", "file", "usr/", "usr/newfile")

    fixture.restorePort1File("usr", oldVersion, None)
    assert os.listdir(str(folder)) == ["oldfile"]

    assert topFile.read() == "new"
    fixture.restorePort1File(".", oldVersion, None)
    assert topFile.read() == "old"

    fixture.restorePort1File(".", newVersion, None)
    assert topFile.read() == "new"
    assert os.listdir(str(folder)) == ["newfile"]
    assert set(os.listdir(str(fixture.loc1))) == { "usr", "samefile", "file" }

class UnidirectionalAugmentedPortSyncerTest(SynchronizerTest):
  def test_shouldSupportAnSSHLocationAtOneOfTheTwoPorts(self, fixture):
    assert "RemoteShellCommand" in fixture.optionNames

    iterToTest(fixture.syncer.ports).shouldContainMatching(
        lambda port: "ssh" in port.supportedProtocols,
        lambda port: "ssh" in port.supportedProtocols)

  def test_shouldWriteToPort2(self, fixture):
    assert fixture.syncer.ports[1].isWrittenTo

