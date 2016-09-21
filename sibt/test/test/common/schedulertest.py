from test.common.builders import schedulingSet

class SchedulerTestFixture(object):
  @property
  def optionInfos(self):
    return self.makeSched().availableOptions
  @property
  def optionNames(self):
    return [optInfo.name for optInfo in self.optionInfos]

  def check(self, schedulings, **kwargs):
    return self.makeSched(**kwargs).check(schedulingSet(schedulings))
