class ValidationException(Exception):
  def __init__(self, errors):
    self.errors = errors

  def __str__(self):
    return "errors when validating rules: " + "\n" + "\n".join(self.errors)

class LocationInvalidException(Exception):
  def __init__(self, path, problem):
    self.path = path
    self.problem = problem

  def __str__(self):
    return "location ‘{0}’ {1}".format(self.path, self.problem)
