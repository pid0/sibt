from datetime import datetime, timezone


class UTCCurrentTimeClock(object):
  def time(self):
    return datetime.now(timezone.utc)
  def localTimeOfDay(self):
    return datetime.now().time()