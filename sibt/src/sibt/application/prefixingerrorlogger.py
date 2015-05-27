class PrefixingErrorLogger(object):
  def __init__(self, output, maximumVerbosity):
    self.output = output
    self.maximumVerbosity = maximumVerbosity
    self.prefix = "sibt: "

  def _prefixedLines(self, lines):
    return [self.prefix + line for line in lines]
  def _indentedLines(self, lines):
    return [len(self.prefix) * " " + line for line in lines]

  def log(self, messageFormat, *args, verbosity=0, continued=False):
    if verbosity > self.maximumVerbosity:
      return

    message = messageFormat
    if len(args) > 0:
      message = messageFormat.format(*args)

    lines = [line for line in message.split("\n")]
    firstLineFunc = self._indentedLines if continued else self._prefixedLines
    self.output.println("\n".join(firstLineFunc(lines[0:1]) + 
      self._indentedLines(lines[1:])))
