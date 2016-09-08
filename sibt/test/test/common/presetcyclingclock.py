class PresetCyclingClock(object):
  def __init__(self, *dateTimes):
    self.dateTimes = list(dateTimes)
    self.cyclingList = list(dateTimes)

  def now(self):
    if len(self.cyclingList) == 0:
      self.cyclingList = list(self.dateTimes)
    return self.cyclingList.pop(0)
