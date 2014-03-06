from sibt.infrastructure.userbasepaths import UserBasePaths
import os

def test_shouldReturnSystemVarAndConfigDirForRootUser():
  rootPaths = UserBasePaths(0)
  assert rootPaths.configDir == "/etc"
  assert rootPaths.varDir == "/var"

def test_shouldReturnSomeUserSpecificDirsIfNotRoot():
  userPaths = UserBasePaths(os.getuid())
  assert userPaths.configDir.endswith("/.sibt/config")
  assert userPaths.varDir.endswith("/.sibt/var")

