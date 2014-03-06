from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode

class SyncRule(CaseClassEqualityHashCode):
  def __init__(self, name, schedulerName, interpreterName):
    self.name = name
    self.schedulerName = schedulerName
    self.interpreterName = interpreterName
    
  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerName, 
      self.interpreterName))
