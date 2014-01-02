import os.path

class ConfigValidator(object):
  def __init__(self, validPrograms):
    self.errorTypes = [
      ('Unknown backup program "{program}" in rule {title}',
      lambda rule: rule.backupProgram not in validPrograms),
      ('Source of rule {title} "{src}" does not exist',
      lambda rule: not os.path.exists(rule.source)),
      ('Source of rule {title} is relative path',
      lambda rule: not os.path.isabs(rule.source)),
      ('Destination of rule {title} is relative path',
      lambda rule: not os.path.isabs(rule.destination)),
      ("Parent of destination of rule {title} does not exist " +
        "(destination: {dest})",
      lambda rule: not os.path.exists(os.path.dirname(
        os.path.abspath(rule.destination))))]
    
  def errorsIn(self, config):
    return sum([self.errorDescriptionsOfType(config, errorType) for errorType in
      self.errorTypes], [])
      
  def errorDescriptionsOfType(self, config, errorType):
    return [errorType[0].format(title = rule.title, dest = rule.destination,
      program = rule.backupProgram, src = rule.source) for rule in 
      self.rulesWithErrorOfType(config, errorType)]
      
  def rulesWithErrorOfType(self, config, errorType):
    return [rule for rule in config.rules if errorType[1](rule)]