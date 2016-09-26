import os
from test.common.assertutil import strToTest

class BufferingOutput(object):
  def __init__(self):
    self.stringBuffer = ""
  
  @property
  def string(self):
    return strToTest(self.stringBuffer)
  
  def println(self, x, lineSeparator=os.linesep):
    self.stringBuffer += str(x) + lineSeparator
