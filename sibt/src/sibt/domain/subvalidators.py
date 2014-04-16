import os.path

class Validator(object):
  def locsOf(self, rule):
    yield rule.loc(1)
    yield rule.loc(2)

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
      for loc in self.locsOf(rule):
        if os.path.isfile(loc):
          return [self.errMsg(loc + " is file, should be folder", rule)]
        if not os.path.isdir(loc):
          return [self.errMsg(loc + " does not exist", rule)]

    return []

class LocAbsoluteValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for loc in self.locsOf(rule):
        if not os.path.isabs(loc):
          return [self.errMsg(loc + " is not absolute", rule)]

    return []

class AcceptingValidator(object):
  def validate(self, rules):
    return []

class LocNotEmptyValidator(Validator):
  def validate(self, rules):
    for rule in rules:
      for loc in self.locsOf(rule):
        if len(os.listdir(loc)) == 0:
          return [self.errMsg(loc + " is empty", rule)]
    return []