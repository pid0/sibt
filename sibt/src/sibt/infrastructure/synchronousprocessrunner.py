import subprocess

class SynchronousProcessRunner(object):
  
  def getOutput(self, program, *arguments):
    return subprocess.check_output([program] + list(arguments)).decode()
  def execute(self, program, *arguments):
    return subprocess.check_call([program] + list(arguments))
