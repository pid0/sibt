class PrefixingErrorLogger(object):
  def __init__(self, output, maximumVerbosity):
    self.output = output
    self.maximumVerbosity = maximumVerbosity

  def log(self, messageFormat, *args, verbosity=0):
    if verbosity > self.maximumVerbosity:
      return

    message = messageFormat
    if len(args) > 0:
      message = messageFormat.format(*args)
    prefixedMessage = "\n".join("sibt: " + line for line in message.split("\n"))
    self.output.println(prefixedMessage)
