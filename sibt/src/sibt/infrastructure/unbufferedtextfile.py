class UnbufferedTextFile(object):
  def __init__(self, bufferedTextFile):
    self.wrappedFile = bufferedTextFile

  def write(self, string):
    self.wrappedFile.write(string)
    self.wrappedFile.flush()
