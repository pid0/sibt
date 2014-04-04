from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from sibt.application.paths import Paths
from test.common.mockedbasepaths import MockedBasePaths

def pathsIn(containerLocalPath, readonlyDir=None):
  return Paths(MockedBasePaths(str(containerLocalPath.join("var")),
    str(containerLocalPath.join("config")), str(readonlyDir) if \
    readonlyDir is not None else str(containerLocalPath.join("read-only"))))

def existingPaths(paths):
  DirTreeNormalizer(paths).createNotExistingDirs()
  return paths
