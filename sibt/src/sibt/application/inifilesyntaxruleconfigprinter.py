import itertools

class IniFileSyntaxRuleConfigPrinter(object):
  def __init__(self, output):
    self.output = output

  def show(self, rule):
    self.output.println("[Scheduler]")
    self._printOptions({"Name": rule.scheduler.name}, rule.schedulerOptions)

    self.output.println("")
    self.output.println("[Synchronizer]")
    self._printOptions({"Name": rule.synchronizer.name},
        rule.synchronizerOptions)

  def _printOptions(self, *optionss):
    for options in optionss:
      for optionKey, optionValue in options.items():
        self.output.println("{0} = {1}".format(optionKey, optionValue))
