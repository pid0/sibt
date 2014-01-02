
class BufferingOutput(object):
  
  def __init__(self):
    self.stdoutBuffer = ""
  
  def println(self, x):
    self.stdoutBuffer += str(x) + "\n"