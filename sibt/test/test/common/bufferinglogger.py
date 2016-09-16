from test.common.assertutil import strToTest

class BufferingLogger(object):
  def __init__(self):
    self.clear()

  @property
  def decoded(self):
    return strToTest(self.buffer.decode())
  
  def write(self, chunk, **kwargs):
    self.buffer += chunk

  def close():
    pass

  def clear(self):
    self.buffer = b""
