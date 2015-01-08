import os

class FileObjOutput(object):
  def __init__(self, fileObject):
    self.fileObject = fileObject
  
  def println(self, x, lineSeparator=os.linesep):
    print(x, file=self.fileObject, end=lineSeparator)
