from test.common.assertutil import strToTest
import os

class BufferingErrorLogger(object):
  def __init__(self):
    self.clear()

  @property
  def string(self):
    return strToTest(self.stringBuffer)
  
  def log(self, messageFormat, *args):
    self.stringBuffer += messageFormat.format(*args) + os.linesep

  def clear(self):
    self.stringBuffer = ""
