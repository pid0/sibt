from sibt.configuration.configuration import Configuration

class ConfigurationBuilder(object):
  def __init__(self):
    self.rules = set()
    self.timeOfDayRestriction = None
    
  def withRules(self, rules):
    self.rules = self.rules | set((rule.build() for rule in rules))
    return self
  def withTimeOfDayRestriction(self, restriction):
    self.timeOfDayRestriction = restriction
    return self
  
  def build(self):
    return Configuration(self.rules, self.timeOfDayRestriction)

def anyConfig():
  return ConfigurationBuilder()
def emptyConfig():
  return ConfigurationBuilder()