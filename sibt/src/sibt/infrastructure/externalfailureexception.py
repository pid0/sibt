class ExternalFailureException(Exception):
  def __init__(self, program, message):
    self.program = program
    self.message = message

  def __str__(self):
    return """error when calling "{0}": {1}""".format(self.program,
        self.message)
