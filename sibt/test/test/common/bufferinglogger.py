from test.common.assertutil import strToTest
import os

class BufferingLogger(object):
  def __init__(self):
    self.stringBuffer = ""

  @property
  def string(self):
    return strToTest(self.stringBuffer)
  
  def log(self, messageFormat, *args):
    self.stringBuffer += messageFormat.format(*args) + os.linesep
