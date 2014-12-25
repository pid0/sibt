class ExternalFailureException(Exception):
  def __init__(self, program, exitStatus):
    self.program = program
    self.exitStatus = exitStatus

  def __str__(self):
    return """error when calling "{0}" ({1})""".format(self.program,
        self.exitStatus)
