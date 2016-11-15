import pytest
from sibt.application.inifilesyntaxruleconfigprinter import \
    IniFileSyntaxRuleConfigPrinter
from test.common.bufferingoutput import BufferingOutput
from test.common.builders import mockRule, fakeConfigurable, mkSyncerOpts
from datetime import timedelta
from sibt.infrastructure import types

class Fixture(object):
  def __init__(self):
    self.output = BufferingOutput()
    self.printer = IniFileSyntaxRuleConfigPrinter(self.output)

@pytest.fixture
def fixture():
  return Fixture()

def ruleWith(**kwargs):
  ret = mockRule(**kwargs)
  ret.scheduler, ret.synchronizer = fakeConfigurable(), fakeConfigurable()
  return ret

def test_shouldFormatOptionValuesBasedOnTheirType(fixture):
  enum = types.Enum("Foo", "Bar")

  rule = ruleWith(
      schedOpts=dict(Encrypt=True, Compress=False),
      syncerOpts=mkSyncerOpts(
      Interval=timedelta(days=5, minutes=1, seconds=2),
      Choice=enum.Bar))

  fixture.printer.show(rule)
  fixture.output.string.shouldIncludeLinePatterns(
      "*Encrypt*Yes*",
      "*Compress*No*",
      "*Interval*5 days 1 minute 2 seconds*",
      "*Choice*Bar*")

def test_shouldFormatZeroTimedeltaCorrectly(fixture):
  fixture.printer.show(ruleWith(schedOpts=dict(Interval=timedelta(seconds=0))))
  fixture.output.string.shouldIncludeLinePatterns("*Interval*0 seconds*")
