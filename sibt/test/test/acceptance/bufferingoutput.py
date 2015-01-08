import os

class BufferingOutput(object):
  
  def __init__(self):
    self.stringBuffer = ""
  
  def println(self, x, lineSeparator=os.linesep):
    self.stringBuffer += str(x) + lineSeparator
