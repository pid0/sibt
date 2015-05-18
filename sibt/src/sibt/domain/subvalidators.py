import os.path
from sibt.domain.syncrule import LocCheckLevel

def formatLoc(loc):
  return "‘{0}’".format(loc)

class ErrorsList(object):
  def __init__(self):
    self.errors = []

  def add(self, message, *rules):
    self.errors.append(self._errMsg(message, rules))

  def _errMsg(self, message, rules):
    return "in " + ", ".join("‘" + rule.name + "’" for rule in rules) + \
        ": " + message

class DiscreteValidator(object):
  def validate(self, ruleSet):
    errorsList = ErrorsList()
    for rule in ruleSet:
      self.checkRule(rule, ruleSet, errorsList)
    return errorsList.errors

class SetsOfTwoValidator(object):
  def validate(self, ruleSet):
    errorsList = ErrorsList()
    ruleList = list(ruleSet)
    for i, rule in enumerate(ruleList):
      for rule2 in ruleList[i+1:]:
        self.checkPair(rule, rule2, errorsList)

    return errorsList.errors
  
class SchedulerCheckValidator(object):
  def validate(self, ruleSet):
    return ["‘{0}’ reported error: {1}".format(*error) for error in 
        ruleSet.schedulerErrors]

class LocExistenceValidator(DiscreteValidator):
  def checkRule(self, rule, ruleSet, errors):
    if rule.options["LocCheckLevel"] == LocCheckLevel.None_:
      return
    for loc in rule.locs:
      if loc.isAFile:
        errors.add(formatLoc(loc) + " is file, should be a folder", rule)
      if not loc.existsAsADir:
        errors.add(formatLoc(loc) + " does not exist", rule)

class LocNotEmptyValidator(DiscreteValidator):
  def checkRule(self, rule, ruleSet, errors):
    if rule.options["LocCheckLevel"] != LocCheckLevel.Strict:
      return
    for loc in rule.locs:
      if loc.isEmpty:
        errors.add(formatLoc(loc) + " is empty", rule)

class NoOverlappingWritesValidator(SetsOfTwoValidator):
  def checkPair(self, rule1, rule2, errors):
    for writeLoc1 in rule1.writeLocs:
      for writeLoc2 in rule2.writeLocs:
        if writeLoc2.contains(writeLoc1) or writeLoc1.contains(writeLoc2):
          errors.add(formatLoc(writeLoc1) + ", " + 
            formatLoc(writeLoc2) + ": overlapping writes", rule1, rule2)

class NoSourceDirOverwriteValidator(DiscreteValidator):
  def checkRule(self, rule, ruleSet, errors):
    for nonWriteLoc in rule.nonWriteLocs:
      for writeLoc in rule.writeLocs:
        if writeLoc.contains(nonWriteLoc):
          errors.add(formatLoc(nonWriteLoc) + " is within " + 
              formatLoc(writeLoc), rule)
