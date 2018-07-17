import pytest
import time
import tarfile

from test.integration.synchronizers.synchronizertest import \
    ListingSynchronizerTest, SynchronizerTest, \
    RunnableFileSynchronizerTestFixture, IncrementalSynchronizerTest, \
    ExcludingSynchronizerTest, UnidirectionalSyncerTest
from test.integration.bashfunctestfixture import \
    BashFuncTestFixture, BashFuncFailedException
from test.common.builders import localLocation, writeFileTree
from test.common import relativeToProjectRoot

class Fixture(RunnableFileSynchronizerTestFixture):
  def __init__(self, tmpdir):
    super().__init__(tmpdir, localLocation, localLocation, localLocation)
    self.load("tar")

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def archiveFileHasContents(archivePath, predicate, expectedContents):
  with tarfile.open(str(archivePath)) as tar:
    member = next(fileInfo for fileInfo in tar.getmembers() if \
        predicate(fileInfo))
    with tar.extractfile(member) as archivedFile:
      return archivedFile.read().decode() == expectedContents

class Test_TarTest(UnidirectionalSyncerTest, IncrementalSynchronizerTest, 
    ExcludingSynchronizerTest):
  @property
  def supportsRecursiveCopying(self):
    return False
  @property
  def minimumDelayBetweenTestsInS(self):
    return 0.025
  @property
  def isMirroring(self):
    return False

  def test_shouldMakeAFullBackupThenANumberOfIncrementsAndKeepOneOldFullBackup(
      self, fixture):
    assert "NumberOfVersions" in fixture.optionNames

    testFile = fixture.loc1 / "file"
    testFile2 = fixture.loc1 / "file2"
    options = dict(NumberOfVersions=3)
    
    def syncWithNewContent(content):
      time.sleep(self.minimumDelayBetweenTestsInS)
      testFile.write(content)
      fixture.sync(options)

    def assertVersions(expectedVersionContents):
      contents = []

      versions = fixture.versionsOf("file", 1, additionalOptions=options)
      assert len(versions) == len(expectedVersionContents)
      for version in sorted(versions):
        fixture.restorePort1File("file", version, None, 
            additionalOptions=options)
        contents.append(testFile.read())

      assert contents == expectedVersionContents

    assertVersions([])

    syncWithNewContent("1")
    assertVersions(["1"])
    syncWithNewContent("2")
    assertVersions(["1", "2"])
    syncWithNewContent("3")
    assertVersions(["1", "2", "3"])

    testFile2.write("first")
    syncWithNewContent("4")
    assertVersions(["1", "2", "3", "4"])
    syncWithNewContent("5")
    assertVersions(["1", "3", "4", "5"])
    syncWithNewContent("6")
    assertVersions(["1", "4", "5", "6"])

    testFile2.write("second")
    syncWithNewContent("7")
    assertVersions(["4", "5", "6", "7"])

    fixture.restorePort1File("file2", sorted(fixture.versionsOf("file2", 1,
      additionalOptions=options))[1], None, additionalOptions=options)
    assert testFile2.read() == "first"

  def test_shouldDumpTheEntireLoc1ToACompressedTarWhenDoingAFullBackup(
      self, fixture):
    assert "Compression" in fixture.optionNames
    assert "gzip" in next(option.optionType.values for option in 
        fixture.syncer.availableOptions if option.name == "Compression")

    quote = "how little, really, they departed from platitude"
    options = dict(Compression="gzip")
    fstab, = writeFileTree(fixture.loc1, [".",
      ["etc",
        "fstab [1]"]])
    fstab.write(quote)

    fixture.sync(options)

    assert archiveFileHasContents(fixture.loc2 / "ar1", 
        lambda info: info.name.endswith("./etc/fstab"), quote)

class ParserFixture(BashFuncTestFixture):
  def __init__(self, tmpdir):
    super().__init__(relativeToProjectRoot("sibt/synchronizers/tar"))
    self.snapshotFile = tmpdir / "snapshot"

  def writeSnapshotFile(self, content):
    with open(str(self.snapshotFile), "wb") as file:
      file.write(content)

  def parse(self, snapshotFileContent, additionalArgs=""):
    self.writeSnapshotFile(snapshotFileContent)
    return self.compute("-parse-snapshot-file '{0}' {1}".format(
      self.snapshotFile, additionalArgs))
  
  def parseTestFile(self, additionalArgs=""):
    return self.parse(
        b"GNU tar-1.28-2\n"
        b"1234\0"
        b"567000000\0"

        b"0\0"
        b"123\0"
        b"123\0"
        b"0\0"
        b"0\0"
        b".\0"
          b"Ddirectory\0"
          b"Ntopfile\0"
          b"\0\0"

        b"0\0"
        b"123\0"
        b"123\0"
        b"0\0"
        b"0\0"
        b"./directory\0"
          b"Yfile\0"
          b"Noldfile\0"
          b"Dsomedir\0"
          b"\0\0"

        b"0\0"
        b"123\0"
        b"123\0"
        b"0\0"
        b"0\0"
        b"./directory/somedir\0"
          b"Ddir3\0"
          b"\0\0"

        b"0\0"
        b"123\0"
        b"123\0"
        b"0\0"
        b"0\0"
        b"./directory/somedir/dir3\0"
          b"Ymain.c"
          b"\0\0", additionalArgs)

@pytest.fixture
def parserFixture(tmpdir):
  return ParserFixture(tmpdir)

class Test_TarSnapshotParserTest(object):
  def test_shouldBeAbleToReadAndOutputTheTimestampEntries(self, parserFixture):
    assert parserFixture.parseTestFile("timestamp") == b"1234,567"

  def test_shouldFailIfFileIsNotInVersion2Format(self, parserFixture):
    with pytest.raises(BashFuncFailedException) as ex:
      parserFixture.parse(b"GNU tar-1.15-1\n")
    assert b"version" in ex.value.stderr
  
  def test_shouldRecursivelyListAllFilesAndDirs(self, parserFixture):
    print(parserFixture.parseTestFile("recursive ."))
    assert parserFixture.parseTestFile("recursive .") == (
        b"topfile\0"
        b"directory/\0"
        b"directory/file\0"
        b"directory/oldfile\0"
        b"directory/somedir/\0"
        b"directory/somedir/dir3/\0"
        b"directory/somedir/dir3/main.c\0")

  def test_shouldBeAbleToListOnlyDirectChildrenOfADir(self, parserFixture):
    assert parserFixture.parseTestFile("direct 'directory/somedir'") == \
        b"dir3/\0"

    assert parserFixture.parseTestFile("direct '.'") == (
        b"directory/\0"
        b"topfile\0")
    assert parserFixture.parseTestFile("direct topfile") == b"topfile\0"

  def test_shouldRecursivelyListAMemberIfGiven(self, parserFixture):
    assert parserFixture.parseTestFile("recursive directory/somedir") == (
        b"dir3/\0"
        b"dir3/main.c\0")
    assert parserFixture.parseTestFile("recursive direc") == b""
    assert parserFixture.parseTestFile("recursive topfile") == b"topfile\0"

  def test_shouldBeAbleToTestForThePresenceOfAMember(self, parserFixture):
    assert parserFixture.parseTestFile("test 'directory/file'") == \
        b"Y"
    assert parserFixture.parseTestFile("test 'directory/foo'") == b""
    assert parserFixture.parseTestFile("test directory") == b"directory"
    assert parserFixture.parseTestFile("test topfile") == b"N"
