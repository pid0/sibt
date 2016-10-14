class Port(object):
  def __init__(self, supportedProtocols, isWrittenTo):
    self.supportedProtocols = supportedProtocols
    self.isWrittenTo = isWrittenTo

  def withAdditionalProtocols(self, *protocols):
    return Port(self.supportedProtocols + list(protocols),
        self.isWrittenTo)

  def canBeAssignedLocation(self, loc):
    return loc.protocol in self.supportedProtocols

  def __repr__(self):
    return "Port{0}".format((self.supportedProtocols))
