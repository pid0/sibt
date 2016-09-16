class SchedulerTestFixture(object):
  @property
  def optionInfos(self):
    return self.makeSched().availableOptions
  @property
  def optionNames(self):
    return [optInfo.name for optInfo in self.optionInfos]
