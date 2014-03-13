from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode

class Scheduling(CaseClassEqualityHashCode):
  def __init__(self, ruleName, options):
    self.ruleName = ruleName
    self.options = options

  def __repr__(self):
    return "Scheduling{0}".format((self.ruleName, self.options))
