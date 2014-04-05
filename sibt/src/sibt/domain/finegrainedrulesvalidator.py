class FineGrainedRulesValidator(object):
  def __init__(self, queuingSchedulers):
    self.queuingScheduler = queuingSchedulers

  def validate(self, rules):
    errors = []
    for rule in rules:
      rule.checkScheduler()
    for scheduler in self.queuingScheduler:
      errors += scheduler.checkAll()
    return errors
