import os.path
from sibt.infrastructure.coprocessrunner import CoprocessRunner
from test.common import relativeToProjectRoot
from sibt.application import configrepo

def loadSynchronizer(absolutePath):
  processRunner = configrepo.createHashbangAwareProcessRunner(
      relativeToProjectRoot("sibt/runners"),
      CoprocessRunner())
  return configrepo.loadSynchronizer(processRunner, absolutePath, 
        os.path.basename(absolutePath))
