from test.common.schedulertest import SchedulerTestFixture
from test.common.builders import buildScheduling, mockSched

class IntermediateSchedulerTestFixture(SchedulerTestFixture):
  def makeSched(self, subCheckErrors=[], subExecute=lambda *_: None):
    wrappedSched = mockSched()
    wrappedSched.execute = subExecute
    wrappedSched.check = lambda *args: subCheckErrors
    return self.construct(wrappedSched)
