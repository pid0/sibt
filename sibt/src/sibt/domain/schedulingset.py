class SchedulingSet(object):
  def __init__(self, schedulings):
    self.schedulings = list(schedulings)
  
  def __iter__(self):
    return iter(self.schedulings)
  def __getitem__(self, index):
    return self.schedulings[index]
  def __len__(self):
    return len(self.schedulings)

  def getSharedOption(self, optionName, defaultValue):
    return self.schedulings[0].options.get(optionName, defaultValue)

  def _checkSchedulingOption(self, checkFunc, scheduling, optionName):
    if optionName not in scheduling.options:
      return None
    return checkFunc(optionName, scheduling.options[optionName], 
        scheduling.ruleName)

  def checkOptionsOfEach(self, checkFunc, *optionNames):
    ret = []
    for scheduling in self.schedulings:
      for optionName in optionNames:
        error = self._checkSchedulingOption(checkFunc, scheduling, optionName)
        if error is not None:
          ret.append(error)
    return ret

  def __repr__(self):
    return "SchedulingSet({0})".format(self.schedulings)
