from sibt.infrastructure.userbasepaths import UserBasePaths
import os

def test_shouldReturnDirsInSystemVarAndConfigDirForRootUser():
  rootPaths = UserBasePaths(0)
  assert rootPaths.configDir == "/etc/sibt"
  assert rootPaths.varDir == "/var/lib/sibt"

def test_shouldReturnSomeUserSpecificDirsIfNotRoot():
  userPaths = UserBasePaths(os.getuid())
  assert userPaths.configDir.endswith("/.sibt/config")
  assert userPaths.varDir.endswith("/.sibt/var")

