import pytest
from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from test.common import mock

class Fixture(object):
  def __init__(self):
    self.maximumVerbosity = 0

  def assertExpectedOutput(self, logInput, formatArgs, expectedOutput):
    output = mock.mock()
    output.expectCalls(mock.call("println", (expectedOutput,)))
    logger = PrefixingErrorLogger(output, 10)
    logger.log(logInput, *formatArgs)
    output.checkExpectedCalls()

  def callsOutputWithVerbosity(self, verbosity, maximum):
    output = mock.mock()
    ret = [False]
    def println(*args):
      ret[0] = True
      return True

    output.expectCalls(mock.callMatching("println", println))
    logger = PrefixingErrorLogger(output, maximum)
    logger.log("""the dark cold enticing with spots of warmth and 
      covered with a sheet of drowsy dimness""", verbosity=verbosity)
    return ret[0]


@pytest.fixture
def fixture():
  return Fixture()

def test_shouldPrintFormattedLogMessagesToOutputWithAPrefixOnEachLine(fixture):
  fixture.assertExpectedOutput("foo {0} baz\nquux", ["bar"],
      "sibt: foo bar baz\nsibt: quux")

def test_shouldNotFormatIfNoFormatArgsAreGiven(fixture):
  logInput = "{0} /file{/bar"
  fixture.assertExpectedOutput(logInput, [], "sibt: " + logInput)

def test_shouldIgnoreLogMessagesThatHaveAVerbosityAboveTheThreshold(fixture):
  assert fixture.callsOutputWithVerbosity(0, maximum=0)
  assert fixture.callsOutputWithVerbosity(0, maximum=1)
  assert fixture.callsOutputWithVerbosity(1, maximum=1)
  assert not fixture.callsOutputWithVerbosity(1, maximum=0)

