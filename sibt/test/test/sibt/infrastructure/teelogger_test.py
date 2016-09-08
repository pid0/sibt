from test.common import mock
from sibt.infrastructure.teelogger import TeeLogger

def test_shouldImmediatelyWriteAnyChunkToAllOfItsSubLoggers():
  chunk = b"abcdef"

  subLogger1 = mock.mock()
  subLogger2 = mock.mock()

  subLogger1.expectCalls(mock.call("write", (chunk,)))
  subLogger2.expectCalls(mock.call("write", (chunk,)))

  logger = TeeLogger(subLogger1, subLogger2)

  logger.write(chunk)

  subLogger1.checkExpectedCalls()
  subLogger2.checkExpectedCalls()

def test_shouldCloseAllSubLoggersWhenItIsClosed():
  subLogger1 = mock.mock()
  subLogger2 = mock.mock()

  subLogger1.expectCalls(mock.call("close", ()))
  subLogger2.expectCalls(mock.call("close", ()))

  with TeeLogger(subLogger1, subLogger2):
    pass

  subLogger1.checkExpectedCalls()
  subLogger2.checkExpectedCalls()

def test_shouldNotCloseUnclosableSubLoggers():
  subLogger = object()

  TeeLogger(subLogger).close()

def test_shouldPassOnAnyGivenKeywordArgsToWriteFuncs():
  subLogger = mock.mock()

  subLogger.expectCalls(mock.callMatching("write", 
    lambda *args, **kwargs: kwargs == dict(Foo="Bar")))

  TeeLogger(subLogger).write(b"", Foo="Bar")

  subLogger.checkExpectedCalls()
