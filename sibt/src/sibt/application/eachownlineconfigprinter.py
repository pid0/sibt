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

  def _printRules(self, rules, areSysRules):
    for rule in rules:
      line = rule.name
      line += " " + "(" + ("enabled" if rule.enabled else "disabled") + ")"
      self.output.println(line)
  def printRules(self, rules):
    self._printRules(rules, False)
  def printSysRules(self, rules):
    self._printRules(rules, True)
      
