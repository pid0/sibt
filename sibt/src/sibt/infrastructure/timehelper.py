from datetime import datetime, timezone
import time

def toUTC(localDateTime):
  timeTuple = localDateTime.timetuple()
  return datetime.fromtimestamp(time.mktime(timeTuple), timezone.utc)
