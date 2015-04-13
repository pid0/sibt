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

  def makeUniqueFolder(self):
    self.testDirNumber += 1
    return self.tmpdir.mkdir("loc-" + str(self.testDirNumber))

  def validSynchronizerLoc(self, name):
    ret = self.tmpdir.join(name)
    if not os.path.isdir(str(ret)):
      os.makedirs(str(ret))
    ret.join("file").write("")
    return str(ret)

  def createSysFolders(self):
    self.sysPaths = existingPaths(self.sysPaths)
  def createReadonlyFolders(self):
    for folder in [self.paths.readonlySchedulersDir, 
        self.paths.readonlySynchronizersDir]:
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

