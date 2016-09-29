from datetime import datetime, timezone
import time

def toUTC(localDateTime):
  timeTuple = localDateTime.timetuple()
  return datetime.fromtimestamp(time.mktime(timeTuple), timezone.utc)

def withoutTimeOfDay(dateTime):
  return datetime(dateTime.year, dateTime.month, dateTime.day, 0, 0, 0, 0, 
      dateTime.tzinfo)
