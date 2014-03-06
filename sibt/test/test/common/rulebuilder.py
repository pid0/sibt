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
    
  testDirCounter = 0
    
  def withName(self, name):
    self.name = name
    return self
  def withScheduler(self, schedulerName):
    self.schedulerName = schedulerName
    return self
  def withInterpreter(self, interpreterName):
    self.interpreterName = interpreterName
    return self
#TODO remove
#  def withExistingSourceAndDest(self, tmpdir):
#    source = str(tmpdir.mkdir("src" + str(RuleBuilder.testDirCounter)))
#    dest = str(tmpdir.mkdir("dest" + str(RuleBuilder.testDirCounter)))
#    self.source = source
#    self.destination = dest
#    RuleBuilder.testDirCounter = RuleBuilder.testDirCounter + 1
#    return self
#  def withExistingAndRelativeSourceAndDest(self, tmpdir):
#    self.withExistingSourceAndDest(tmpdir)
#    self.source = os.path.relpath(self.source)
#    self.destination = os.path.relpath(self.destination)
#    return self
    
  def build(self):
    return SyncRule(self.name, self.schedulerName, self.interpreterName)

def anyRule(): return RuleBuilder() 
