class ValidatorCollectionValidator(object):
  def __init__(self, validators):
    self.validators = validators

  def validate(self, rules):
    for validator in self.validators:
      errors = validator.validate(rules)
      if len(errors) > 0:
        return errors
    
    return []

