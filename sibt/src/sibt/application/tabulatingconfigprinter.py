from sibt.infrastructure.tableprinter import TablePrinter

def getOrNone(getFunc):
  try:
    return getFunc()
  except AttributeError:
    return None

def isLoaded(rule):
  return hasattr(rule, "scheduler")

class TabulatingConfigPrinter(object):
  def __init__(self, output, useColors, maxWidth, dateTimeFormatter):
    self.output = output
    self.timeFormatter = dateTimeFormatter
    self.tablePrinter = TablePrinter(self.output, useColors, maxWidth)

  def _printNames(self, objects):
    for obj in objects:
      self.output.println(obj.name)

  def printSynchronizers(self, synchronizers):
    self._printNames(synchronizers)

  def printSchedulers(self, synchronizers):
    self._printNames(synchronizers)

  def _printRules(self, rules, *columns, printHeaders=True):
    sortedRules = sorted(rules, key=lambda rule: rule.name)

    self.tablePrinter.print(sortedRules, *columns, printHeaders=printHeaders)

  def printSimpleRuleListing(self, rules):
    self._printRules(rules, Name(), Enabled(), printHeaders=False)

  def printFullRuleListing(self, rules):
    self._printRules(rules, 
        Name(), LastTime(self.timeFormatter), 
        LastStatus(self.timeFormatter), NextTime(self.timeFormatter))

class Name(object):
  header = "Name"
  def formatCell(self, rule):
    return rule.name

class Enabled(object):
  header = "Enabled?"
  def formatCell(self, rule):
    return "[Enabled]" if rule.enabled else "[Disabled]"

class TimeCol(object):
  def __init__(self, timeFormatter):
    self.timeFormatter = timeFormatter
  def formatCell(self, rule):
    time = self.extractTime(rule)
    if time is None:
      return None
    return self.timeFormatter.format(time)

class LastTime(TimeCol):
  header = "Last Execution"
  def extractTime(self, rule):
    return getOrNone(lambda: rule.lastExecutionTime)

class LastStatus(object):
  def __init__(self, timeFormatter):
    self.timeFormatter = timeFormatter
    self.header = "Last Status"

  def formatCell(self, rule):
    if rule.executing:
      return "Executing since {0}".format(
          self.timeFormatter.format(rule.currentExecution.startTime))
    succeeded = getOrNone(lambda: rule.lastFinishedExecution.succeeded)
    return { True: "Succeeded", False: "Failed", None: None }[succeeded]

class NextTime(TimeCol):
  header = "Next Execution"
  def extractTime(self, rule):
    return getOrNone(lambda: rule.nextExecution.startTime)
