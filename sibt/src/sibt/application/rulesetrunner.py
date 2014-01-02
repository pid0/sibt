class RuleSetRunner(object):
  def __init__(self, processRunner, rulesFilter, ruleInterpreters):
    self.processRunner = processRunner
    self.rulesFilter = rulesFilter
    self.ruleInterpreters = ruleInterpreters
  
  def runRules(self, rules):
    for rule in self.rulesFilter.getDueRules(rules):
      self.ruleInterpreters[rule.backupProgram].processRule(
        rule, self.processRunner)