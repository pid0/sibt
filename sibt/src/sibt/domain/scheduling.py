from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode

class Scheduling(CaseClassEqualityHashCode):
  def __init__(self, ruleName, options, lastExecutionTime):
    self.ruleName = ruleName
    self.options = options
    self.lastExecutionTime = lastExecutionTime

  def __repr__(self):
    return "Scheduling{0}".format((self.ruleName, self.options, 
      self.lastExecutionTime))
