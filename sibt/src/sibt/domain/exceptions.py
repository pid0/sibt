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

class LocationNotAbsoluteException(LocationInvalidException):
  def __init__(self, stringRepresentation):
    super().__init__(stringRepresentation, "is not absolute")

class UnsupportedProtocolException(Exception):
  def __init__(self, ruleName, optionName, protocol, supportedProtocols=[],
      explanation=""):
    self.optionName = optionName
    self.protocol = protocol
    self.supportedProtocols = supportedProtocols
    self.ruleName = ruleName
    self.explanation = explanation

  def __str__(self):
    return ("rule ‘{0}’: {1} can't have {2} protocol{3}{4}").format(
        self.ruleName, self.optionName, self.protocol, 
        (" because " + self.explanation) if self.explanation != "" else "",
        ("; choose from " + ", ".join(self.supportedProtocols)) if \
            self.supportedProtocols != [] else "")
