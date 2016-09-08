from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode

class SchedulingLogging(CaseClassEqualityHashCode):
  def __init__(self, startTime, output, result):
    self.startTime = startTime
    self.output = output
    self._result = result
    self.finished = result is not None

    if self.finished:
      self.endTime = result.endTime
      self.succeeded = result.succeeded
  
  def __repr__(self):
    return "SchedulingLogging{0}".format((self.startTime, self.output, 
      self._result))

class SchedulingResult(CaseClassEqualityHashCode):
  def __init__(self, endTime, succeeded):
    self.endTime = endTime
    self.succeeded = succeeded
  
  def __repr__(self):
    return "SchedulingResult{0}".format((self.endTime, self.succeeded))
