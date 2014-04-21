class IniFileSyntaxRuleConfigPrinter(object):
  def __init__(self, output):
    self.output = output

  def show(self, rule):
    self.output.println("[Scheduler]")
    self._printOptions(rule.schedulerOptions)

    self.output.println("")
    self.output.println("[Interpreter]")
    self._printOptions(rule.interpreterOptions)

  def _printOptions(self, options):
    for optionKey, optionValue in options.items():
      self.output.println("{0} = {1}".format(optionKey, optionValue))
