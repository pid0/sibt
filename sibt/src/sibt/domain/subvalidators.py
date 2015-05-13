import os.path
from sibt.domain.syncrule import LocCheckLevel

def formatLoc(loc):
  return "‘{0}’".format(loc)

class Validator(object):
  def errMsg(self, message, *rules):
    return "in " + ", ".join("‘" + rule.name + "’" for rule in rules) + \
        ": " + message
  
class SchedulerCheckValidator(Validator):
  def validate(self, ruleSet):
    return ["‘{0}’ reported error: {1}".format(*error) for error in 
        ruleSet.schedulerErrors]

class LocExistenceValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      if rule.options["LocCheckLevel"] == LocCheckLevel.None_:
        continue
      for loc in rule.locs:
        if loc.isAFile:
          return [self.errMsg(formatLoc(loc) + 
            " is file, should be folder", rule)]
        if not loc.existsAsADir:
          return [self.errMsg(formatLoc(loc) + " does not exist", rule)]

    return []

class AcceptingValidator(object):
  def validate(self, ruleSet):
    return []

class LocNotEmptyValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      if rule.options["LocCheckLevel"] != LocCheckLevel.Strict:
        continue
      for loc in rule.locs:
        if loc.isEmpty:
          return [self.errMsg(formatLoc(loc) + " is empty", rule)]
    return []

class NoOverlappingWritesValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      for rule2 in ruleSet:
        if rule is rule2:
          continue
        for writeLoc1 in rule.writeLocs:
          for writeLoc2 in rule2.writeLocs:
            if writeLoc2.contains(writeLoc1):
              return [self.errMsg(formatLoc(writeLoc1) + ", " + 
                formatLoc(writeLoc2) + ": overlapping writes", rule, rule2)]

    return []

class NoSourceDirOverwriteValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      for nonWriteLoc in rule.nonWriteLocs:
        for writeLoc in rule.writeLocs:
          if writeLoc.contains(nonWriteLoc):
            return [self.errMsg(formatLoc(nonWriteLoc) + 
              " is within " + formatLoc(writeLoc), rule)]

    return []
