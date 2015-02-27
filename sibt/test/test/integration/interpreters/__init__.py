import os.path
from sibt.domain.defaultvalueinterpreter import DefaultValueInterpreter
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.application.configrepo import createHashbangAwareProcessRunner
from sibt.infrastructure.coprocessrunner import \
    CoprocessRunner
from test.common import relativeToProjectRoot

def loadInterpreter(absolutePath):
  processRunner = createHashbangAwareProcessRunner(
      relativeToProjectRoot("sibt/runners"),
      CoprocessRunner())
  return DefaultValueInterpreter(
      ExecutableFileRuleInterpreter(absolutePath, 
        os.path.basename(absolutePath), processRunner))
