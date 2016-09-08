from datetime import datetime, timezone

class CurrentTimeClock(object):
  def now(self):
    return datetime.now(timezone.utc)
