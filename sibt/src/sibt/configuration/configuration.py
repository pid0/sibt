from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode


class Configuration(CaseClassEqualityHashCode):
  def __init__(self, rules, timeOfDayRestriction):
    self.rules = rules
    self.timeOfDayRestriction = timeOfDayRestriction
    
  def __repr__(self):
    return "Configuration({0})".format((self.rules, self.timeOfDayRestriction))