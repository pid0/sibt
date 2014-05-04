class InterpreterFuncNotImplementedException(Exception):
  def __init__(self, interpreterPath, funcName):
    self.interpreterPath = interpreterPath
    self.funcName = funcName

  def __str__(self):
    return "interpreter {0} doesn't implement {1}".format(self.interpreterPath,
        self.funcName)