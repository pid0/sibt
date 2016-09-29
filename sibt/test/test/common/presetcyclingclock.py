class PresetCyclingClock(object):
  def __init__(self, *dateTimes):
    self.dateTimes = dateTimes

  def getDateTimes(self):
    return self._originalDateTimes
  
  def setDateTimes(self, dateTimes):
    self._originalDateTimes = list(dateTimes)
    self._cyclingList = list(dateTimes)

  dateTimes = property(getDateTimes, setDateTimes)

  def now(self):
    if len(self._cyclingList) == 0:
      self._cyclingList = list(self._originalDateTimes)
    return self._cyclingList.pop(0)
