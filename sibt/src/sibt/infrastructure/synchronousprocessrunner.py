import subprocess

class SynchronousProcessRunner(object):
  
  def execute(self, program, *arguments):
    return subprocess.check_call([program] + list(arguments))
