from test.common.presetcyclingclock import PresetCyclingClock
from test.common.builders import anyUTCDateTime
from datetime import datetime, timezone

def test_shouldCycleThroughAListOfPresetTimes():
  firstTime = datetime.now(timezone.utc)
  secondTime = anyUTCDateTime()

  clock = PresetCyclingClock(firstTime, secondTime)

  assert [clock.now(), clock.now(), clock.now(), clock.now(), clock.now()] == \
      [firstTime, secondTime, firstTime, secondTime, firstTime]
