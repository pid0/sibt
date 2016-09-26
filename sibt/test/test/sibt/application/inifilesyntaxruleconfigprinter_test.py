from sibt.application.inifilesyntaxruleconfigprinter import \
    IniFileSyntaxRuleConfigPrinter
from test.common.bufferingoutput import BufferingOutput
from test.common.builders import mockRule, fakeConfigurable, mkSyncerOpts
from datetime import timedelta
from sibt.infrastructure import types

def test_shouldFormatOptionValuesBasedOnTheirType():
  output = BufferingOutput()
  printer = IniFileSyntaxRuleConfigPrinter(output)
  enum = types.Enum("Foo", "Bar")

  rule = mockRule(
      schedOpts=dict(Encrypt=True, Compress=False),
      syncerOpts=mkSyncerOpts(
      Interval=timedelta(days=5, minutes=1, seconds=2),
      Choice=enum.Bar))
  rule.scheduler, rule.synchronizer = fakeConfigurable(), fakeConfigurable()

  printer.show(rule)
  output.string.shouldIncludeLinePatterns(
      "*Encrypt*Yes*",
      "*Compress*No*",
      "*Interval*5 days 1 minute 2 seconds*",
      "*Choice*Bar*")
