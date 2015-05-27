from datetime import time, datetime

class EachOwnLineConfigPrinter(object):
  def __init__(self, output):
    self.output = output

  def _printNames(self, objects):
    for obj in objects:
      self.output.println(obj.name)

  def printSynchronizers(self, synchronizers):
    self._printNames(synchronizers)

  def printSchedulers(self, synchronizers):
    self._printNames(synchronizers)

  def _printRules(self, rules):
    for rule in rules:
      line = rule.name
      line += " " + "(" + ("enabled" if rule.enabled else "disabled") + ")"
      self.output.println(line)

  def printSimpleRuleListing(self, rules):
    self._printRules(rules)

  def printFullRuleListing(self, rules):
    for rule in rules:
      if not hasattr(rule, "scheduler"):
        continue
      self.output.println(rule.name)
      
