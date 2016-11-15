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
    with subprocess.Popen(["bash", "-c", 
      "source '{0}' {1}\n".format(self.libraryFilePath, 
        self.libraryArguments) + code], 
      stderr=subprocess.PIPE, stdout=subprocess.PIPE) as process:
      stdout, stderr = process.communicate()

    sys.stderr.write(stderr.decode())
    if process.returncode != 0:
      raise BashFuncFailedException(stderr)

    return stdout
