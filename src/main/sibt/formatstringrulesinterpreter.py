
class FormatStringRulesInterpreter(object):
  
  def __init__(self, formatString, sourceTransformer):
    formatArgs = formatString.split(' ')
    
    self.program = formatArgs[0]
    self.args = formatArgs[1:] 
    self.sourceTransformer = sourceTransformer
  
  def processRule(self, rule, programRunner):
    substitutedArgs = [self.sourceTransformer(rule.source) if arg == "{src}"
      else rule.destination if arg == "{dest}" else arg for arg in self.args]
    programRunner.execute(self.program, *substitutedArgs)