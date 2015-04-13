class ValidationException(Exception):
  def __init__(self, errors):
    self.errors = errors

  def __str__(self):
    return "errors when validating rules: " + "\n" + "\n".join(self.errors)

class LocationInvalidException(Exception):
  def __init__(self, stringRepresentation, problem):
    self.stringRepresentation = stringRepresentation
    self.problem = problem

  def __str__(self):
    return "location ‘{0}’ {1}".format(self.stringRepresentation, self.problem)

class UnsupportedProtocolException(Exception):
  def __init__(self, ruleName, optionName, protocol, supportedProtocols):
    self.optionName = optionName
    self.protocol = protocol
    self.supportedProtocols = supportedProtocols
    self.ruleName = ruleName

  def __str__(self):
    return ("rule ‘{0}’: {1} can't have protocol ‘{2}’, choose from " + 
      "‘{3}’").format(self.ruleName, self.optionName, self.protocol, 
        ", ".join(self.supportedProtocols))
