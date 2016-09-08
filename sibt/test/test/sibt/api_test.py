from sibt import api
from test.common.pathsbuilder import pathsIn
import os.path

def test_shouldMakeUserPathsThatDontExistWhenOpeningLog(tmpdir):
  paths = pathsIn(tmpdir)
  api.openLog(sibtPaths=paths, sibtSysPaths=None)

  assert os.path.isdir(str(paths.logDir))

def test_shouldBeAbleToIgnoreUserPaths():
  api.openLog(sibtPaths=None, sibtSysPaths=None)
