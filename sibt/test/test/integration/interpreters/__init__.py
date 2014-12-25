import os.path
from sibt.domain.defaultvalueinterpreter import DefaultValueInterpreter
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.application.configrepo import createHashbangAwareProcessRunner
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner

def loadInterpreter(absolutePath):
  processRunner = createHashbangAwareProcessRunner("sibt/runners",
      SynchronousProcessRunner())
  return DefaultValueInterpreter(
      ExecutableFileRuleInterpreter(absolutePath, 
        os.path.basename(absolutePath), processRunner))
