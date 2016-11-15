from sibt.application.toplevelloginterface import TopLevelLogInterface
from sibt.application.paths import Paths
from sibt.infrastructure.userbasepaths import UserBasePaths
from sibt.main import createNotExistingDirs

CurrentUserPaths = object()
SystemPaths = object()

def openLog(sibtPaths=CurrentUserPaths, sibtSysPaths=SystemPaths):
  if sibtPaths is CurrentUserPaths:
    sibtPaths = Paths(UserBasePaths.forCurrentUser())
  if sibtSysPaths is SystemPaths:
    sibtSysPaths = Paths(UserBasePaths(0))

  if sibtPaths is not None:
    createNotExistingDirs(sibtPaths)

  return TopLevelLogInterface(sibtPaths, sibtSysPaths)
