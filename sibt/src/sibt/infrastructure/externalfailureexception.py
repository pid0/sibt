class ExternalFailureException(Exception):
  def __init__(self, program, arguments, exitStatus):
    self.program = program
    self.arguments = arguments
    self.exitStatus = exitStatus

  def __str__(self):
    return "error when calling “{0}” with arguments {1} ({2})".format(
        self.program, self.arguments, self.exitStatus)
