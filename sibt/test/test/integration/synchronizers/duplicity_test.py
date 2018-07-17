import pytest
import time
import os
from datetime import datetime, timezone
import glob
import subprocess
import shutil
import tarfile
import io
import tempfile

from test.common import relativeToProjectRoot
from test.integration.davserver import DAVServer

from test.common.builders import localLocation, port
from test.integration.synchronizers.synchronizertest import \
    SynchronizerTest, UnidirectionalSyncerTest, IncrementalSynchronizerTest, \
    RunnableFileSynchronizerTestFixture, remoteLocationFromPath

from test.integration.bashfunctestfixture import \
    BashFuncTestFixture, BashFuncFailedException

GPGKeyFilePath = os.path.join(os.path.dirname(__file__), "encryption-key")
GPGKeyID = "B7855E056E695DF2"

class GPG:
  def __init__(self, gpgHome):
    self.envVars = dict(os.environ)
    self.envVars["GNUPGHOME"] = str(gpgHome)

    self.call("--import", GPGKeyFilePath)
    with tempfile.NamedTemporaryFile() as ownertrust:
      ownertrust.write(b"E027C5BB4777F0BED29F78E3B7855E056E695DF2:6:\n")
      ownertrust.seek(0, 0)
      self.call("--import-ownertrust", stdin=ownertrust)

  def call(self, *args, stdout=None, stdin=None):
    subprocess.check_call(
        ["gpg"] + list(args),
        stdout=stdout,
        stdin=stdin,
        env=self.envVars)

def chezdavDependenciesRunning():
  ps = subprocess.Popen(["ps", "aux"], stdout=subprocess.PIPE)
  grep1 = subprocess.Popen(["grep", "-v", "grep"], stdin=ps.stdout,
      stdout=subprocess.PIPE)
  grep2 = subprocess.Popen(["grep", "avahi-daemon"], stdin=grep1.stdout,
      stdout=subprocess.PIPE)
  return len(grep2.communicate()[0]) != 0

def chezdavAvailable():
  return shutil.which("chezdav") is not None and chezdavDependenciesRunning()

class Fixture(RunnableFileSynchronizerTestFixture):
  def __init__(self, tmpdir, location2FromPathFunc):
    super().__init__(tmpdir, localLocation, location2FromPathFunc,
        localLocation)
    self.load("duplicity")
    self.archiveDir = tmpdir.mkdir("archive")

    self.davServer = None
    if location2FromPathFunc is DAVLocation:
      if not chezdavAvailable():
        pytest.skip("chezdav is required")
      self.davServer = DAVServer.start(str(self.loc2.dirname))
      self.location2FromPath = lambda _: remoteLocationFromPath("dav",
          self.davServer.port)("/" + str(self.loc2.basename))

  def optsWith(self, options):
    ret = super().optsWith(options)
    ret["ArchiveDir"] = localLocation(str(self.archiveDir))
    return ret

  def stopServer(self):
    if self.davServer is not None:
      self.davServer.stop()

DAVLocation = object()

@pytest.fixture(params=[DAVLocation, localLocation])
def fixture(request, tmpdir):
  loc2Func = request.param
  ret = Fixture(tmpdir, loc2Func)
  request.addfinalizer(ret.stopServer)
  return ret

class Test_DuplicityTest(UnidirectionalSyncerTest, IncrementalSynchronizerTest):
  @property
  def supportsRecursiveCopying(self):
    return False
  @property
  def minimumDelayBetweenTestsInS(self):
    return 1

  def test_shouldMakeDuplicityEncryptTheBackupWithGPGIfAKeyIsGiven(
      self, fixture):
    assert "KeyID" in fixture.optionNames
    assert "GPGHome" in fixture.optionNames

    testFile = fixture.loc1 / "file"
    testFile.write("secret")

    gpgHome = fixture.tmpdir / "gpg"
    gpgHome.mkdir()
    gpg = GPG(gpgHome)

    options = dict(KeyID=GPGKeyID, GPGHome=localLocation(gpgHome))
    fixture.sync(options)

    encryptedDifftar = glob.glob(
        str(fixture.loc2 / "duplicity-full*difftar.*"))[0]
    difftarPath = str(fixture.tmpdir / "difftar.tar.gz")

    with open(difftarPath, "wb") as difftar:
      gpg.call("--decrypt", encryptedDifftar, stdout=difftar)

    with tarfile.open(difftarPath) as difftar:
      with difftar.extractfile("snapshot/file") as fileInBackup:
        assert fileInBackup.read() == b"secret"

  def test_shouldSupportOnlyFileAtPort1AndSeveralProtocolsAtPort2(
      self, fixture):
    fixture.protocolsOfPort(1).shouldContain("file")
    fixture.protocolsOfPort(2).shouldInclude("file", "ssh", "dav")

class FileListingFilterFixture(BashFuncTestFixture):
  def __init__(self, tmpdir):
    super().__init__(relativeToProjectRoot("sibt/synchronizers/duplicity"))

  def rewrite(self, input):
    return self.compute("-rewrite-file-listing", input=input)

@pytest.fixture
def filterFixture(tmpdir):
  return FileListingFilterFixture(tmpdir)

class Test_DuplicityFileListingFilterTest(object):
  def test_shouldOutputZeroSeparatedRawFileNamesFromAfterTheRootFolder(
      self, filterFixture):
    assert filterFixture.rewrite(rb"""
foo
. bar

INFO 10 20001231T153030Z '.' dir
. Sun Dec 31 15:30:30 2000 .

INFO 10 20001231T153030Z 'file1' reg
. Sun Dec 31 15:30:30 2000 file1

INFO 10 20001231T153030Z 'file2' reg
. Sun Dec 31 15:30:30 2000 file2""") == b"file1\0file2\0"

  def test_shouldIncludeNewlinesInFileNamesThatHaveThem(self, filterFixture):
    assert filterFixture.rewrite(rb"""
INFO 10 20001231T153030Z '.' dir
. Sun Dec 31 15:30:30 2000 .

INFO 10 20001231T153030Z 'folder/\n. fi$'\nle' reg
. Sun Dec 31 15:30:30 2000 
. . fi$'
. le""") == b"\n. fi$'\nle\0"

    assert filterFixture.rewrite(rb"""
INFO 10 20001231T153030Z '.' dir
. Sun Dec 31 15:30:30 2000 .

INFO 10 20001231T153030Z '\nfoo' reg
. Sun Dec 31 15:30:30 2000 
. foo

NOTICE ...""") == b"\nfoo\0"

  def test_shouldAppendSlashesToDirectories(self, filterFixture):
    assert filterFixture.rewrite(rb"""
INFO 10 20001231T153030Z '.' dir
. Sun Dec 31 15:30:30 2000 .

INFO 10 20001231T153030Z 'foo/s\nub' dir
. Sun Dec 31 15:30:30 2000 foo/s
. ub

INFO 10 20001231T153030Z 'folder' dir
. Sun Dec 31 15:30:30 2000 folder""") == b"foo/s\nub/\0folder/\0"
