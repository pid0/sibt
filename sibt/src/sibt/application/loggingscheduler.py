from sibt.infrastructure import types
from sibt.domain.optioninfo import OptionInfo
from sibt.application.execenvironment import ExecEnvironment

from sibt.infrastructure.teelogger import TeeLogger
from sibt.infrastructure.filelogger import FileLogger
from sibt.infrastructure.utillinuxsyslogger import UtilLinuxSysLogger

import traceback

Options = [
    OptionInfo("LogFile", types.File),
    OptionInfo("Stderr", types.Bool),
    OptionInfo("Syslog", types.Bool),
    OptionInfo("SyslogOptions", types.String),
    OptionInfo("LogSuccess", types.Bool)]

class _UnclosableFile(object):
  def __init__(self, file, respectIgnore=False):
    self.file = file
    self.respectIgnore = respectIgnore

  def write(self, chunk, **kwargs):
    if self.respectIgnore and "ignore" in kwargs:
      return
    self.file.write(chunk)

class _FileLikeOutputWrapper(object):
  def __init__(self, output):
    self.output = output

  def write(self, chunk, **kwargs):
    self.output.println(chunk.decode(), lineSeparator="")

class LoggingScheduler(object):
  def __init__(self, wrapped, clock, stderr, forceLoggingToStderr):
    self._wrapped = wrapped
    self._clock = clock
    self._stderr = stderr
    self._forceLoggingToStderr = forceLoggingToStderr

    self.availableOptions = wrapped.availableOptions + Options
  
  def _makeSubLoggersFor(self, scheduling):
    ret = []

    if "LogFile" in scheduling.options:
      ret.append(FileLogger(str(scheduling.options["LogFile"]),
        self._clock, scheduling.ruleName))

    if scheduling.options.get("Stderr", False) or self._forceLoggingToStderr:
      ret.append(_FileLikeOutputWrapper(self._stderr))

    if scheduling.options.get("Syslog", True):
      ret.append(UtilLinuxSysLogger(scheduling.options.get("SyslogOptions", ""),
        prefix=scheduling.ruleName.encode(), tag="sibt"))

    return ret

  def execute(self, execEnv, scheduling):
    with TeeLogger(
        _UnclosableFile(execEnv.binaryLogger, respectIgnore=True),
        *self._makeSubLoggersFor(scheduling)) as logger:
      try:
        succeeded = self._wrapped.execute(execEnv.withLoggerReplaced(logger), 
            scheduling)
      except BaseException as ex:
        logger.write("internal exception when executing rule ‘{0}’:\n".format(
          scheduling.ruleName).encode(), severity="err", ignore=True)
        message = traceback.format_exc() if isinstance(ex, Exception) else \
            str(ex)
        logger.write((message + "\n").encode(), severity="err", ignore=True)
        raise

      if not succeeded:
        logger.write("execution of rule ‘{0}’ failed\n".format(
          scheduling.ruleName).encode(), severity="err", ignore=True)

      if succeeded and scheduling.options.get("LogSuccess", False):
        logger.write("rule ‘{0}’ successfully executed\n".format(
          scheduling.ruleName).encode(), severity="notice", ignore=True)

      return succeeded

  def __getattr__(self, name):
    return getattr(self._wrapped, name)
