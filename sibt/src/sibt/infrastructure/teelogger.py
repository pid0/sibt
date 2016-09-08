class TeeLogger(object):
  def __init__(self, *subLoggers):
    self.subLoggers = subLoggers

  def write(self, chunk, **kwargs):
    for subLogger in self.subLoggers:
      subLogger.write(chunk, **kwargs)
  
  def close(self):
    for subLogger in self.subLoggers:
      if hasattr(subLogger, "close"):
        subLogger.close()

  def __enter__(self):
    return self
  def __exit__(self, exceptionType, ex, traceback):
    self.close()
