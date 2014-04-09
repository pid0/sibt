import pytest
from datetime import datetime, timezone, timedelta
from sibt.domain.version import Version

def test_shouldThrowExceptionIfItReceivesAnUnaware():
  with pytest.raises(Exception):
    Version("name", datetime(2013, 5, 3, 20, 10, 3))

  Version("name", datetime(2014, 2, 10, tzinfo=timezone(timedelta(hours=5))))

def test_shouldBeAbleToConvertTheTimeToAUTCRepresentationString():
  assert Version("", datetime(2015, 3, 6, 18, 15, 30, 
      tzinfo=timezone(timedelta(hours=2)))).timeAsUTCW3C == \
      "2015-03-06T16:15:30"

