import os
import sys

def encode(string):
  return string.encode(sys.getdefaultencoding(), errors="surrogateescape")

class FileObjOutput(object):
  def __init__(self, fileObject):
    self.fileObject = fileObject
  
  def println(self, x, lineSeparator=os.linesep):
    self.fileObject.write(encode(x))
    self.fileObject.write(encode(lineSeparator))
