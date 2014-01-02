class ConfigParseException(Exception):
  def __init__(self, file, message):
    self.file = file
    self.message = message
    
  def __str__(self):
    return 'ConfigParseException: {0} in file "{1}"'.format(
      self.message, self.file)