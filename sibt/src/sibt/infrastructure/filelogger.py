from sibt.infrastructure.linebufferedlogger import LineBufferedLogger

TimeFormat = "%Y-%m-%d %H:%M:%S"

class FileLogger(LineBufferedLogger):
  def __init__(self, filePath, clock, prefix=""):
    super().__init__()
    self.file = open(filePath, "ab")
    self.clock = clock
    self.prefix = prefix
    self.startingNewLine = True

  def writeLine(self, line, **kwargs):
    prefix = "[{0}, {1}] ".format(
        self.clock.now().strftime(TimeFormat), 
        self.prefix)
    self.file.write(prefix.encode())

    self.file.write(line)
    if line[-1:] != b"\n":
      self.file.write(b"\n")
    self.file.flush()

  def close(self):
    super().close()
    self.file.close()
