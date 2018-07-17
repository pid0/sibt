import pytest
from sibt.application.datetimeformatter import DateTimeFormatter
from test.common.builders import constantTimeClock
from test.common.assertutil import strToTest
from datetime import datetime, timezone

def makeFormatter(currentTime=None):
  if currentTime is None:
    currentTime = datetime.now(timezone.utc)
  return DateTimeFormatter(constantTimeClock(currentTime), True)

class Fixture(object):
  def make(self, currentTime):
    return makeFormatter(currentTime)
  
  def formattedString(self, dateTime, now=None):
    return strToTest(self.make(now).format(dateTime))

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldFormatDateTimeAsALocalizedStringIfNotParticularlyClose(fixture):
  time = datetime(1985, 11, 23, 10, 25, 0, 0, timezone.utc)
  fixture.formattedString(time).shouldInclude("1985", "23", "10", "25").\
      but.shouldNotInclude("ago", "in", "tomorrow", "yesterday")

def test_shouldWriteMinutesAndSecondsUntilDateTimeIfCloseEnough(fixture):
  now = datetime(1990, 1, 1, 2, 0, 0, 0, timezone.utc)

  time = datetime(1990, 1, 1, 6, 20, 10, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldInclude("In 4h20m")

  time = datetime(1990, 1, 1, 1, 35, 10, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldInclude("25m ago")

  time = datetime(1990, 1, 1, 2, 59, 40, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldInclude("In 1h")

def test_shouldWriteYesterdayOrTomorrowOrToday(fixture):
  now = datetime(1990, 1, 10, 23, 0, 0, 0, timezone.utc)

  time = datetime(1990, 1, 11, 10, 27, 0, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldInclude("Tomorrow", "10", "27")

  time = datetime(1990, 1, 9, 5, 27, 0, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldInclude("Yesterday", "5", "27")

  time = datetime(1990, 1, 10, 5, 27, 0, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldInclude("Today", "5", "27")

def test_shouldFormatNowSpecially(fixture):
  now = datetime(1990, 5, 5, 0, 0, 0, 0, timezone.utc)
  time = datetime(1990, 5, 5, 0, 0, 30, 0, timezone.utc)
  fixture.formattedString(time, now=now).shouldBe("About now")
