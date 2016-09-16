from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from sibt.infrastructure.fileobjoutput import FileObjOutput

class _TextModeFileLike(object):
  def __init__(self, binaryModeFileLike):
    self.wrapped = binaryModeFileLike
  
  def write(self, string):
    self.wrapped.write(string.encode())

class ExecEnvironment(object):
  def __init__(self, syncUncontrolledCall, logger, logSubProcessWith):
    self._syncUncontrolledCall = syncUncontrolledCall
    self._logSubProcessWith = logSubProcessWith
    self.binaryLogger = logger
    self.logger = PrefixingErrorLogger(FileObjOutput(
      _TextModeFileLike(self.binaryLogger)), "scheduler", 0)

  def runSynchronizer(self):
    return self._logSubProcessWith(self.binaryLogger, 
        self._syncUncontrolledCall) == 0
  
  def logSubProcess(self, *args, **kwargs):
    return self._logSubProcessWith(self.binaryLogger, *args, **kwargs)

  def withLoggerReplaced(self, newBinaryLogger):
    return ExecEnvironment(self._syncUncontrolledCall,
        newBinaryLogger, self._logSubProcessWith)
