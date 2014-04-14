from datetime import time, datetime
from sibt import executiontimeprediction

class EachOwnLineConfigPrinter(object):
  def __init__(self, output):
    self.output = output

  def _printNames(self, objects):
    for obj in objects:
      self.output.println(obj.name)

  def printInterpreters(self, interpreters):
    self._printNames(interpreters)

  def printSchedulers(self, interpreters):
    self._printNames(interpreters)

  def _printRules(self, rules, areSysRules):
    for rule in rules:
      line = ("+" if areSysRules else "-") + rule.name
      line += " " + "(" + ("enabled" if rule.enabled else "disabled") + ")"
      self.output.println(line)
  def printRules(self, rules):
    self._printRules(rules, False)
  def printSysRules(self, rules):
    self._printRules(rules, True)
      
#  def _formatExecutionTime(self, pointInTime):
#    return ("n/a" if pointInTime is None else
#      "Due" if pointInTime is executiontimeprediction.Due else
#      datetime.strftime(pointInTime, "%Y-%m-%d %H:%M:%S.%f %z"))
    
