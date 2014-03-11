class RunResult(object):
  def __init__(self, stdout, stderr, exitStatus):
    self.stdout = stdout
    self.exitStatus = exitStatus
    self.stderr = stderr
