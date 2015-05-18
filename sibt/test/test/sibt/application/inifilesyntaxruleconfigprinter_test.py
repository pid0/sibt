from sibt.application.inifilesyntaxruleconfigprinter import \
    IniFileSyntaxRuleConfigPrinter
from test.common.bufferingoutput import BufferingOutput
from test.common.assertutil import strToTest
from test.common import mock
from test.common.builders import fakeConfigurable, mkSyncerOpts
from datetime import timedelta
from sibt.infrastructure import types

def test_shouldFormatOptionValuesBasedOnTheirType():
  output = BufferingOutput()
  printer = IniFileSyntaxRuleConfigPrinter(output)
  enum = types.Enum("Foo", "Bar")
  rule = mock.mock()
  rule.options = {}
  rule.scheduler, rule.synchronizer = fakeConfigurable(), fakeConfigurable()
  rule.schedulerOptions = dict(Encrypt=True, Compress=False)
  rule.synchronizerOptions = mkSyncerOpts(
      Interval=timedelta(days=5, minutes=1, seconds=2),
      Choice=enum.Bar)

  printer.show(rule)
  strToTest(output.stringBuffer).shouldIncludeLinePatterns(
      "*Encrypt*Yes*",
      "*Compress*No*",
      "*Interval*5 days 1 minute 2 seconds*",
      "*Choice*Bar*")
