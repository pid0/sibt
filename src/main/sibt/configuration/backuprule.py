from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode

class BackupRule(CaseClassEqualityHashCode):
  def __init__(self, title, backupProgram, sourceDir, destDir, interval=None):
    self.title = title
    self.backupProgram = backupProgram
    self.source = sourceDir
    self.destination = destDir
    self.interval = interval
    
  def __repr__(self):
    return "BackupRule{0}".format((self.title, self.backupProgram, 
      self.source, self.destination, self.interval))