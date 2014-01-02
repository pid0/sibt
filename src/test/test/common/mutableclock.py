from datetime import datetime, timezone

class MutableClock(object):
  
  def __init__(self, time, timeOfDay):
    self.currentTime = time
    self.timeOfDay = timeOfDay
    
  @classmethod
  def fromUTCNow(cls):
    return MutableClock(datetime.now(timezone.utc), 
      datetime.now().time())
  
  def putForward(self, delta):
    self.currentTime = self.currentTime + delta
  def setDateTime(self, time):
    self.currentTime = time
  
  def time(self):
    return self.currentTime
  def localTimeOfDay(self):
    return self.timeOfDay