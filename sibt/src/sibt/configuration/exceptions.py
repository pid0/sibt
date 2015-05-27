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
          furtherDescription), file=file)
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
    return "error in configuration of {0}{1} (‘{2}’): {3}".format(
        self.unitType, (" " + self.unitName) if 
        self.unitName is not None else "", self.file, self.message)

class MissingConfigValuesException(ConfigSyntaxException):
  def __init__(self, unitType, unitName, file=None):
    super().__init__(unitType, unitName, "can't resolve option values", file)

class ConfigurableNotFoundException(ConfigConsistencyException):
  def __init__(self, unitType, unitName, message, ruleName, file=None):
    super().__init__(unitType, unitName, message, file=file)
    self.ruleName = ruleName

  def __str__(self):
    return "{0}{1} of rule ‘{2}’ (‘{3}’) not found{4}".format(self.unitType,
        (" ‘" + self.unitName + "’") if self.unitName is not None else "", 
        self.ruleName, self.file, 
        (": " + self.message) if self.message is not None else "")

class OptionParseException(Exception):
  def __init__(self, errors):
    self.errors = errors

  def __str__(self):
    return "parse errors:\n" + "\n".join(str(error) for error in self.errors)

class OptionParseError(object):
  def __init__(self, optionName, stringToParse, expectedType, message):
    self.optionName = optionName
    self.stringToParse = stringToParse
    self.expectedType = expectedType
    self.message = message

  def __str__(self):
    return "value {0} of option {1} is no {2} because {3}".format(
        repr(self.stringToParse), self.optionName, self.expectedType,
        self.message)

  def __repr__(self):
    return "OptionParseError{0}".format((self.optionName, self.stringToParse,
      self.expectedType, self.message))

