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
  def test_shouldBeAbleToListDirectoriesInLoc1AsTheyWereInThePastNotRecursively(
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
