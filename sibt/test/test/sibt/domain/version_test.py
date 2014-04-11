import pytest
from datetime import datetime, timezone, timedelta
from sibt.domain.version import Version

def test_shouldThrowExceptionIfItReceivesAnUnawareTime():
  ruleMock = lambda x:x
  ruleMock.name = "name"

  with pytest.raises(Exception):
    Version(ruleMock, datetime(2013, 5, 3, 20, 10, 3))

  Version(ruleMock, datetime(2014, 2, 10, tzinfo=timezone(timedelta(hours=5))))

def test_shouldBeAbleToShowItselfAsCommaSeparatedStringWithUTCTime():
  ruleMock = lambda x:x
  ruleMock.name = "some-rule"
  assert Version(ruleMock, datetime(2015, 3, 6, 18, 15, 30, 
      tzinfo=timezone(timedelta(hours=2)))).strWithUTCW3C == \
      "some-rule,2015-03-06T16:15:30"

