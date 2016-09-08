import subprocess
import shlex
import os
from sibt.infrastructure.exceptions import ExternalFailureException
from sibt.infrastructure.linebufferedlogger import LineBufferedLogger

class UtilLinuxSysLogger(LineBufferedLogger):
  def __init__(self, loggerOptions, prefix=None, 
      facility="user", severity="info", tag=None):
    super().__init__()

    self.prefix = b""
    if prefix is not None:
      self.prefix = prefix + b": "

    self.loggerOptions = loggerOptions
    
    self.facility = facility
    self.severity = severity
    self.tag = tag

  def writeLine(self, line, facility=None, severity=None, **kwargs):
    facility = facility or self.facility
    severity = severity or self.severity

    priority = "{0}.{1}".format(facility, severity)

    execArgs = ["logger"] + shlex.split(self.loggerOptions) + \
        ["--id={0}".format(os.getpid()), "--priority", priority] + \
        (["--tag", self.tag] if self.tag is not None else [])

    with subprocess.Popen(execArgs, stdin=subprocess.PIPE) as loggerProcess:
      loggerProcess.stdin.write(self.prefix + line)

    if loggerProcess.returncode != 0:
      raise ExternalFailureException(execArgs[0], execArgs[1:], 
          loggerProcess.returncode)
