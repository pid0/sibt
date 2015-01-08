import subprocess
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException

class SynchronousProcessRunner(object):
  def _wrappingException(self, func):
    try:
      return func()
    except subprocess.CalledProcessError as ex:
      raise ExternalFailureException(ex.cmd[0], ex.cmd[1:], 
          ex.returncode) from ex
    
  def getOutput(self, program, *arguments, delimiter="\n"):
    def getSplitOutput():
      outputBytes = subprocess.check_output([program] + list(arguments))
      string = outputBytes.decode()
      if len(string) == 0:
        return []
      split = string.split(delimiter)
      return split[:-1] if string.endswith(delimiter) else split

    return self._wrappingException(getSplitOutput)

  def execute(self, program, *arguments):
    return self._wrappingException(lambda: 
        subprocess.check_call([program] + list(arguments)))
