class ValidatorCollectionValidator(object):
  def __init__(self, validatorGroups):
    self.validatorGroups = validatorGroups

  def validate(self, rules):
    for validatorGroup in self.validatorGroups:
      errors = []
      for validator in validatorGroup:
        errors.extend(validator.validate(rules))
      if len(errors) > 0:
        return errors
    
    return []

