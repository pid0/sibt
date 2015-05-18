class SynchronizerFuncNotImplementedException(Exception):
  def __init__(self, synchronizerName, funcName):
    self.synchronizerName = synchronizerName
    self.funcName = funcName

  def __str__(self):
    return "synchronizer ‘{0}’ does not implement ‘{1}’".format(
        self.synchronizerName, self.funcName)

class ExternalFailureException(Exception):
  def __init__(self, program, arguments, exitStatus):
    self.program = program
    self.arguments = arguments
    self.exitStatus = exitStatus

  def __str__(self):
    return "error when calling “{0}” with arguments {1} ({2})".format(
        self.program, self.arguments, self.exitStatus)

class ModuleFunctionNotImplementedException(Exception):
  def __init__(self, funcName):
    self.funcName = funcName

class ParseException(Exception):
  def __init__(self, parsedString, error):
    self.parsedString = parsedString
    self.error = error

  def __str__(self):
    return "error when parsing ‘{0}’: {1}".format(
        repr(self.parsedString), self.error)
