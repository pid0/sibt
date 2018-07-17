# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from sibt.infrastructure import collectFilesInDirs
from test.common.assertutil import iterToTest

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.folder1 = tmpdir.join("folder1")
    self.folder1.mkdir()
    self.folder2 = tmpdir.join("folder2")
    self.folder2.mkdir()

    self.name1 = "file1"
    self.name2 = "some-file2"
    self.name3 = "bar"

  def writeFiles(self):
    self.folder1.join(self.name1).write("")
    self.folder1.join(self.name2).write("")
    self.folder2.join(self.name3).write("")

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_collectFuncShouldCallFunctionForEachFileInDirsAndCollectResultsInASet(
    fixture):
  fixture.writeFiles()
  assert iterToTest(collectFilesInDirs(
      [str(fixture.folder1), str(fixture.folder2)], 
      lambda path, fileName: (path, fileName))).shouldContainInAnyOrder(
          (str(fixture.folder1 / fixture.name1), fixture.name1),
          (str(fixture.folder1 / fixture.name2), fixture.name2),
          (str(fixture.folder2 / fixture.name3), fixture.name3))

def test_collectFunctionShouldLeaveOutNoneValues(fixture):
  fixture.writeFiles()
  iterToTest(collectFilesInDirs([str(fixture.folder1)], lambda _, name: 
      "ab" if name == fixture.name1 else None)).shouldContain("ab")

def test_collectFunctionShouldIgnoreDirsThatDontExist(fixture):
  fixture.writeFiles()
  assert len(collectFilesInDirs([str(fixture.folder2), "/does-not-exist"],
    lambda x, y: (x, y))) == 1

def test_collectFunctionShouldIgnoreDirsWithinTheSpecifiedDirs(fixture):
  fixture.writeFiles()
  fixture.folder2.join("a-dir").mkdir()
  assert len(collectFilesInDirs([str(fixture.folder2)], lambda *x: x)) == 1

def test_collectFunctionShouldCallFunctionWithAbsolutePaths(fixture):
  fixture.writeFiles()
  with fixture.tmpdir.as_cwd():
    iterToTest(collectFilesInDirs(["folder2"], lambda path, _: path)).\
        shouldContainInAnyOrder(str(fixture.folder2.join(fixture.name3)))

def test_shouldIgnoreDotFiles(fixture):
  fixture.writeFiles()
  fixture.folder2.join(".hidden").write("")

  assert len(collectFilesInDirs([str(fixture.folder2)], 
      lambda path, _: path)) == 1
