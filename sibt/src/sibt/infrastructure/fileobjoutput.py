class FileObjOutput(object):
  def __init__(self, fileObject):
    self.fileObject = fileObject
  
  def println(self, x):
    print(x, file=self.fileObject)
