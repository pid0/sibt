class ExecutionLogger(object):
  
  def __init__(self):
    self.programsList = []
  
  def execute(self, program, *arguments):
    self.programsList.append((program, arguments))