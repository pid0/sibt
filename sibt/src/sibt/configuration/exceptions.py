class ConfigConsistencyException(Exception):
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return "config consistency error: {0}".format(self.message)

class ConfigSyntaxException(Exception):
  def __init__(self, file, message):
    self.file = file
    self.message = message
    
  def __str__(self):
    return 'invalid syntax in file {0}: {1}'.format(
      self.file, self.message)
