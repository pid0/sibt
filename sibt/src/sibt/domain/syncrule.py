from sibt.domain.scheduling import Scheduling
from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode

#aggregate (SyncRule, scheduler, interpreter) root
class SyncRule(object):
  def __init__(self, name, schedulerOptions, interpeterOptions, enabled, 
      scheduler, interpreter):
    self.name = name
    self.schedulerOptions = schedulerOptions
    self.interpreterOptions = interpeterOptions
    self.enabled = enabled
    self.scheduler = scheduler
    self.interpreter = interpreter

  def schedule(self):
    self.scheduler.run([Scheduling(self.name, self.schedulerOptions)])
  def sync(self):
    self.interpreter.sync(self.interpreterOptions)

  def schedulerName(self):
    return self.scheduler.name
  def interpreterName(self):
    return self.scheduler.name
  schedulerName = property(schedulerName)
  interpreterName = property(interpreterName)
    
  def __repr__(self):
    return "SyncRule{0}".format((self.name, self.schedulerOptions, 
      self.interpreterOptions, self.enabled, self.scheduler, self.interpreter))
