import os
import sys

class InterceptingOutput(object):
  @classmethod
  def stderr(clazz):
    def setStderr(newFile):
      sys.stderr = newFile
    return clazz(sys.stderr, setStderr, 2)
  @classmethod
  def stdout(clazz):
    def setStdout(newFile):
      sys.stdout = newFile
    return clazz(sys.stdout, setStdout, 1)

  def __init__(self, fileObject, setter, fd):
    self.fileObject = fileObject
    self.originalFd = -1
    self.newFile = None
    self.setter = setter
    self.fd = fd

  def __enter__(self):
    self.fileObject.flush()
    self.originalFd = os.dup(self.fd)
    readEnd, writeEnd = os.pipe()
    self.newFile = os.fdopen(writeEnd, "w")
    self.readFile = os.fdopen(readEnd, "r")
    self.setter(self.newFile)
    os.dup2(writeEnd, self.fd)

    return self

  def __exit__(self, exceptionType, ex, traceback):
    self.newFile.flush()
    self.newFile.close()
    self.setter(os.fdopen(self.originalFd, "w"))
    os.dup2(self.originalFd, self.fd)

    self.stringBuffer = self.readFile.read()
    self.readFile.close()

  def println(self, x):
    print(x, file=self.newFile)

