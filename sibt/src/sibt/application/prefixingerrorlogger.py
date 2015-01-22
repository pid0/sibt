class PrefixingErrorLogger(object):
  def __init__(self, output, maximumVerbosity):
    self.output = output
    self.maximumVerbosity = maximumVerbosity
    self.prefix = "sibt: "

  def log(self, messageFormat, *args, verbosity=0):
    if verbosity > self.maximumVerbosity:
      return

    message = messageFormat
    if len(args) > 0:
      message = messageFormat.format(*args)
    lines = [line for line in message.split("\n")]
    prefixedMessage = "\n".join([self.prefix + lines[0]] +
        [len(self.prefix) * " " + line for line in lines[1:]])
    self.output.println(prefixedMessage)
