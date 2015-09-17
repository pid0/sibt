import pytest
from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from test.common import mock

class Fixture(object):
  def __init__(self):
    self.maximumVerbosity = 0

  def getLoggedOutput(self, logInput, *formatArgs, maxVerbosity=10, 
      prefix="sibt", **kwargs):
    output = mock.mock()
    ret = [None]
    def storeResult(string):
      ret[0] = string
      return True

    output.expectCalls(mock.callMatching("println", storeResult))
    logger = PrefixingErrorLogger(output, prefix, maxVerbosity)

    logger.log(logInput, *formatArgs, **kwargs)
    return ret[0]

  def callsOutputWithVerbosity(self, verbosity, maximum):
    return self.getLoggedOutput(\
        """the dark cold enticing with spots of warmth and 
        covered with a sheet of drowsy dimness""", maxVerbosity=maximum,
        verbosity=verbosity) is not None

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldPrintFormattedLogMessagesWithAPrefixAndIndentation(fixture):
  prefix = "master-control"
  assert fixture.getLoggedOutput("foo {0} baz\nquux", "bar", prefix=prefix) == \
        "master-control: foo bar baz\n" + \
        (" " * len(prefix + ": ")) + \
        "quux"
  assert fixture.getLoggedOutput("{0} {1}", "the", "rest", continued=True) == \
      "      the rest"

def test_shouldNotFormatIfNoFormatArgsAreGiven(fixture):
  logInput = "{0} /file{/bar"
  fixture.getLoggedOutput(logInput) == "sibt: " + logInput

def test_shouldIgnoreLogMessagesThatHaveAVerbosityAboveTheThreshold(fixture):
  assert fixture.callsOutputWithVerbosity(0, maximum=0)
  assert fixture.callsOutputWithVerbosity(0, maximum=1)
  assert fixture.callsOutputWithVerbosity(1, maximum=1)
  assert not fixture.callsOutputWithVerbosity(1, maximum=0)

