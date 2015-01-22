class ValidationException(Exception):
  def __init__(self, errors):
    self.errors = errors

  def __str__(self):
    return "errors when validating rules: " + "\n" + "\n".join(self.errors)
