class FineGrainedRulesValidator(object):
  def validate(self, rules):
    errors = []
    for rule in rules:
      errors += rule.checkScheduler()
    return errors
