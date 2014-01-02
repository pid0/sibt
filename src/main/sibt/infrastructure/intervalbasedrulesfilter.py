from sibt import executiontimeprediction
from datetime import datetime

class IntervalBasedRulesFilter(object):
  
  def __init__(self, executionTimeRepo, clock):
    self.clock = clock
    self.executionTimeRepo = executionTimeRepo
  
  def _dueRulesGen(self, rules):
    for rule in rules:
      if rule.interval is None:
        yield rule
        continue
      
      executionTime = self.lastExecutionTimeOf(rule)
      if (executionTime is None or 
        self.clock.time() - executionTime >= rule.interval):
        yield rule
        
  def getDueRules(self, rules):
    return set(self._dueRulesGen(rules))
  
  def lastExecutionTimeOf(self, rule):
    return self.executionTimeRepo.executionTimeOf(rule)
  
  def predictNextExecutionTimeOf(self, rule, illegalTimeRange=None):
    lastExecutionTime = self.lastExecutionTimeOf(rule)
    if lastExecutionTime is None:
      return executiontimeprediction.Due
    
    nextExecutionTime = (lastExecutionTime + rule.interval if 
      rule.interval is not None else self.clock.time())
    if (illegalTimeRange is not None and 
      nextExecutionTime.time() in illegalTimeRange):
      newTime = illegalTimeRange.end
      nextExecutionTime = datetime.combine(nextExecutionTime, newTime).replace(
        tzinfo=nextExecutionTime.tzinfo, minute=newTime.minute + 1)
      
    if self.clock.time() >= nextExecutionTime:
      return executiontimeprediction.Due
    return nextExecutionTime