import subprocess
import sys

class BashFuncFailedException(Exception):
  def __init__(self, stderr):
    self.stderr = stderr

class BashFuncTestFixture(object):
  def __init__(self, libraryFilePath, libraryArguments=""):
    self.libraryFilePath = libraryFilePath
    self.libraryArguments = libraryArguments
  
  def compute(self, code):
    result = subprocess.run(["bash", "-c", 
      "source '{0}' {1}\n".format(self.libraryFilePath, 
        self.libraryArguments) + code], 
      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    sys.stderr.write(result.stderr.decode())
    if result.returncode != 0:
      raise BashFuncFailedException(result.stderr)

    return result.stdout
