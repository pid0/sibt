class UnbufferedFile(object):
  def __init__(self, bufferedFile):
    self.wrappedFile = bufferedFile

  def write(self, x):
    self.wrappedFile.write(x)
    self.wrappedFile.flush()

  def flush(self):
    self.wrappedFile.flush()
