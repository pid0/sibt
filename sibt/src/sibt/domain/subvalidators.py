import os.path
from sibt.infrastructure.pathhelper import isPathWithinPath

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
      for loc in rule.locs:
        if os.path.isfile(loc):
          return [self.errMsg(loc + " is file, should be folder", rule)]
        if not os.path.isdir(loc):
          return [self.errMsg(loc + " does not exist", rule)]

    return []

class LocAbsoluteValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      for loc in rule.locs:
        if not os.path.isabs(loc):
          return [self.errMsg(loc + " is not absolute", rule)]

    return []

class AcceptingValidator(object):
  def validate(self, ruleSet):
    return []

class LocNotEmptyValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      for loc in rule.locs:
        if len(os.listdir(loc)) == 0:
          return [self.errMsg(loc + " is empty", rule)]
    return []

class NoOverlappingWritesValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      for rule2 in ruleSet:
        if rule is rule2:
          continue
        for writeLoc1 in rule.writeLocs:
          for writeLoc2 in rule2.writeLocs:
            if isPathWithinPath(writeLoc1, writeLoc2):
              return [self.errMsg(writeLoc1 + ", " + writeLoc2 + 
                  ": overlapping writes", rule, rule2)]

    return []

class NoSourceDirOverwriteValidator(Validator):
  def validate(self, ruleSet):
    for rule in ruleSet:
      for nonWriteLoc in rule.nonWriteLocs:
        for writeLoc in rule.writeLocs:
          if isPathWithinPath(nonWriteLoc, writeLoc):
            return [self.errMsg(nonWriteLoc + " within " + writeLoc)]

    return []
