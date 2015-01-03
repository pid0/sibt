class ConfigConsistencyException(Exception):
  def __init__(self, unitType, unitName, message, file=None):
    self.unitType = unitType
    self.unitName = unitName
    self.message = message
    self.file = file

  def __str__(self):
    return "{0} ‘{1}’ ({2}) inconsistent: {3}".format(self.unitType,
        self.unitName, self.file, self.message)

class ConfigSyntaxException(Exception):
  def __init__(self, unitType, message, file=None):
    self.unitType = unitType
    self.message = message
    self.file = file

  def __str__(self):
    return "syntax error in configuration of a {0} ({1}): {2}".format(
        self.unitType, self.file, self.message)
