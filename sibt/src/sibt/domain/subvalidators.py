import os.path
from sibt.infrastructure.pathhelper import isPathWithinPath

class Validator(object):
  def errMsg(self, message, *rules):
    return "in " + ", ".join(rule.name for rule in rules) + ": " + message
  
class SchedulerCheckValidator(Validator):
  def __init__(self, queuingSchedulers):
    self.queuingScheduler = queuingSchedulers

  def validate(self, rules):
    errors = []
    for rule in rules:
      rule.checkScheduler()
    for scheduler in self.queuingScheduler:
      errors += scheduler.checkAll()
    return [self.errMsg(error, *rules) for error in errors]

class LocExistenceValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for loc in rule.locs:
        if os.path.isfile(loc):
          return [self.errMsg(loc + " is file, should be folder", rule)]
        if not os.path.isdir(loc):
          return [self.errMsg(loc + " does not exist", rule)]

    return []

class LocAbsoluteValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for loc in rule.locs:
        if not os.path.isabs(loc):
          return [self.errMsg(loc + " is not absolute", rule)]

    return []

class AcceptingValidator(object):
  def validate(self, rules):
    return []

class LocNotEmptyValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for loc in rule.locs:
        if len(os.listdir(loc)) == 0:
          return [self.errMsg(loc + " is empty", rule)]
    return []

class NoOverlappingWritesValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for rule2 in rules:
        if rule is rule2:
          continue
        for writeLoc1 in rule.writeLocs:
          for writeLoc2 in rule2.writeLocs:
            if isPathWithinPath(writeLoc1, writeLoc2):
              return [self.errMsg(writeLoc1 + ", " + writeLoc2 + 
                  ": overlapping writes", rule, rule2)]

    return []

class NoSourceDirOverwriteValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for nonWriteLoc in rule.nonWriteLocs:
        for writeLoc in rule.writeLocs:
          if isPathWithinPath(nonWriteLoc, writeLoc):
            return [self.errMsg(nonWriteLoc + " within " + writeLoc)]

    return []
