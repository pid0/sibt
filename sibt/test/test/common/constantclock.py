from datetime import datetime, timezone

class ConstantClock(object):
  
  def __init__(self, constantTime, timeOfDay):
    self.constantTime = constantTime
    self.timeOfDay = timeOfDay
    
  @classmethod
  def fromUTCNow(cls):
    return ConstantClock(datetime.now(timezone.utc), 
      datetime.now().time())
  
  def putForward(self, delta):
    return ConstantClock(self.constantTime + delta, self.timeOfDay)
  
  def time(self):
    return self.constantTime
  def localTimeOfDay(self):
    return self.timeOfDay