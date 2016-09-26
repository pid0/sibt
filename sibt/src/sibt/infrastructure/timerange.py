from sibt.infrastructure.caseclassequalityhashcode \
  import CaseClassEqualityHashCode
from datetime import time

class TimeRange(CaseClassEqualityHashCode):
  def __init__(self, inclusiveStart, inclusiveEnd):
    self.start = inclusiveStart
    self.end = inclusiveEnd
    
  def __contains__(self, other):
    if self.start > self.end:
      return not (other > self.end and other < self.start)
    return other >= self.start and other <= self.end
    
  def __repr__(self):
    return "TimeRange{0}".format((self.start, self.end))

def fullTimeRange():
  return TimeRange(time.min, time.max)
def timeRange(start, end):
  return TimeRange(start, end)
