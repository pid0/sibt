from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from sibt.infrastructure.fileobjoutput import FileObjOutput

class ExecEnvironment(object):
  def __init__(self, syncCall, logger, logSubProcessWith):
    self._syncCall = syncCall
    self._logSubProcessWith = logSubProcessWith
    self.binaryLogger = logger
    self.logger = PrefixingErrorLogger(FileObjOutput(self.binaryLogger),
        "scheduler", 0)

  def runSynchronizer(self):
    return self._logSubProcessWith(self.binaryLogger, self._syncCall) == 0
  
  def logSubProcess(self, *args, **kwargs):
    return self._logSubProcessWith(self.binaryLogger, *args, **kwargs)

  def withLoggerReplaced(self, newBinaryLogger):
    return ExecEnvironment(self._syncCall, newBinaryLogger, 
        self._logSubProcessWith)
