class ConfigConsistencyException(Exception):
  def __init__(self, unitType, unitName, message, file=None):
    self.unitType = unitType
    self.unitName = unitName
    self.message = message
    self.file = file

  def __str__(self):
    return "{0} ‘{1}’ (‘{2}’) inconsistent: {3}".format(self.unitType,
        self.unitName, self.file, self.message)

class RuleNameInvalidException(ConfigConsistencyException):
  def __init__(self, ruleName, invalidCharacter, furtherDescription="", 
      file=None):
    super().__init__("rule", ruleName, 
        "has invalid character in its name: ‘{0}’ {1}".format(invalidCharacter,
          furtherDescription))
    self.invalidCharacter = invalidCharacter

  def __str__(self):
    return "{0} ‘{1}’ (‘{2}’) {3}".format(self.unitType,
        self.unitName, self.file, self.message)

class ConfigSyntaxException(Exception):
  def __init__(self, unitType, unitName, message, file=None):
    self.unitType = unitType
    self.message = message
    self.unitName = unitName
    self.file = file

  def __str__(self):
    return "error in configuration of {0} {1} (‘{2}’): {3}".format(
        self.unitType, self.unitName, self.file, self.message)
