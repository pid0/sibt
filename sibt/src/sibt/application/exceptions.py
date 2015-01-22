class RuleNameMismatchException(Exception):
  def __init__(self, ruleName):
    self.ruleName = ruleName

  def __str__(self):
    return "no rule with name ‘{0}’".format(self.ruleName)

class RulePatternsMismatchException(Exception):
  def __init__(self, patterns):
    self.patterns = patterns

  def __str__(self):
    return "no rule matching patterns ‘{0}’".format(", ".join(
      "‘" + pattern + "’" for pattern in self.patterns))
