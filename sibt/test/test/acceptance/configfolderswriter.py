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

import os
import shutil
from test.common.pathsbuilder import existingPaths, pathsIn
from py.path import local

class ConfigFoldersWriter(object):
  def __init__(self, sysPaths, paths, tmpdir):
    self.sysPaths = sysPaths
    self.paths = paths
    self.tmpdir = tmpdir
    self.testDirNumber = 100

  def uniqueFolderName(self):
    self.testDirNumber += 1
    return "loc-" + str(self.testDirNumber)

  def validSynchronizerLoc(self, name, isEmpty=False):
    ret = self.tmpdir.join(name)
    if not os.path.isdir(str(ret)):
      os.makedirs(str(ret))
    if not isEmpty:
      ret.join("file").write("")
    return str(ret)

  def createReadonlyFolders(self):
    for folder in [
        self.paths.readonlySchedulersDir, 
        self.paths.readonlySynchronizersDir,
        self.paths.readonlyIncludesDir]:
      os.makedirs(folder)

  def deleteConfigAndVarFolders(self):
    for directory in os.listdir(str(self.tmpdir)):
      shutil.rmtree(str(self.tmpdir) + "/" + directory)

  def writeRunner(self, name):
    os.makedirs(self.paths.runnersDir)
    runnerPath = local(self.paths.runnersDir).join(name)
    runnerPath.write("#!/usr/bin/env bash\necho $1")
    runnerPath.chmod(0o700)
    return str(runnerPath)

