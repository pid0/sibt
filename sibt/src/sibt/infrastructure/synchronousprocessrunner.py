import subprocess
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException

class SynchronousProcessRunner(object):
  def _wrappingException(self, program, func):
    try:
      return func()
    except subprocess.CalledProcessError as ex:
      raise ExternalFailureException(program, ex.returncode) from ex
    
  def getOutput(self, program, *arguments):
    return self._wrappingException(program, 
        lambda: subprocess.check_output([program] + list(arguments)).decode())
  def execute(self, program, *arguments):
    return self._wrappingException(program, 
        lambda: subprocess.check_call([program] + list(arguments)))
