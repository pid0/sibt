class RuleNotFoundException(Exception):
  pass

class RuleNameMismatchException(RuleNotFoundException):
  def __init__(self, ruleName):
    self.ruleName = ruleName

  def __str__(self):
    return "no rule with name ‘{0}’".format(self.ruleName)

class RulePatternMismatchException(RuleNotFoundException):
  def __init__(self, pattern):
    self.pattern = pattern

  def __str__(self):
    return "no rule matching pattern ‘{0}’".format(self.pattern)
