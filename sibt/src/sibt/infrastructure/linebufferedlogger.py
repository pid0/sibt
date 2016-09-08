class LineBufferedLogger(object):
  def __init__(self):
    self.__buffer = b""

  def write(self, chunk, **kwargs):
    lines = chunk.split(b"\n")
    for i, line in enumerate(lines[:-1]):
      fullLine = line + b"\n"
      if i == 0:
        fullLine = self.__buffer + fullLine
      self.writeLine(fullLine, **kwargs)

    if len(lines) > 1:
      self.__buffer = b""
    self.__buffer += lines[-1]

  def close(self):
    if len(self.__buffer) > 0:
      self.writeLine(self.__buffer)
