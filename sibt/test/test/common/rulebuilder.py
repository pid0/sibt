from sibt.domain.syncrule import SyncRule
from random import random
import os.path

def randstring():
  return str(random())[2:] 
  
def withRandstring(string):
  return string + randstring()

class RuleBuilder(object):
  def __init__(self):
    self.name = withRandstring("any-name")
    self.schedulerName = withRandstring("any-scheduler")
    self.interpreterName = withRandstring("any-interpreter")
    self.enabled = True
    
  def withName(self, name):
    self.name = name
    return self
  def withScheduler(self, schedulerName):
    self.schedulerName = schedulerName
    return self
  def withInterpreter(self, interpreterName):
    self.interpreterName = interpreterName
    return self
  def disabled(self):
    self.enabled = False
    return self
    
  def build(self):
    return SyncRule(self.name, self.schedulerName, self.interpreterName, 
        self.enabled)

def anyRule(): return RuleBuilder() 

