
class BufferingOutput(object):
  
  def __init__(self):
    self.stringBuffer = ""
  
  def println(self, x):
    self.stringBuffer += str(x) + "\n"
