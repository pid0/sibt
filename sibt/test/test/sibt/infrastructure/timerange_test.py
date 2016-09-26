from datetime import time
from sibt.infrastructure.timerange import TimeRange

def test_shouldContainATimeIfItIsBetweenOrEqualToItsLimits():
  timeRange = TimeRange(time(15, 23), time(19, 57))
  
  assert time(15, 23) in timeRange
  assert time(19, 57) in timeRange
  assert time(16, 15) in timeRange
  assert time(19, 58) not in timeRange
  assert time(22, 0) not in timeRange
  assert time(15, 22) not in timeRange
  
  rangeAcrossWrapPoint = TimeRange(time(18, 10), time(4, 3))
  
  assert time(18, 10) in rangeAcrossWrapPoint
  assert time(20, 0) in rangeAcrossWrapPoint
  assert time(0, 0) in rangeAcrossWrapPoint
  assert time(4, 3) in rangeAcrossWrapPoint
  assert time(6, 15) not in rangeAcrossWrapPoint
  assert time(12, 0) not in rangeAcrossWrapPoint
  assert time(18, 9) not in rangeAcrossWrapPoint
