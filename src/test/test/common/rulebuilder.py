from sibt.configuration.backuprule import BackupRule
from random import random
import os.path

def randstring():
  return str(random())[2:] 
  
def withRandstring(string):
  return string + randstring()

class RuleBuilder(object):
  def __init__(self):
    self.title = withRandstring("any-title")
    self.program = withRandstring("any-program")
    self.source = withRandstring("any-source/a")
    self.destination = withRandstring("any-dest/b")
    self.interval = None
    
  testDirCounter = 0
    
  def withSource(self, source):
    self.source = source
    return self
  def withDest(self, dest):
    self.destination = dest
    return self
  def withTitle(self, title):
    self.title = title
    return self
  def withProgram(self, program):
    self.program = program
    return self
  def withInterval(self, interval):
    self.interval = interval
    return self
  def withoutInterval(self):
    return self
  def withExistingSourceAndDest(self, tmpdir):
    source = str(tmpdir.mkdir("src" + str(RuleBuilder.testDirCounter)))
    dest = str(tmpdir.mkdir("dest" + str(RuleBuilder.testDirCounter)))
    self.source = source
    self.destination = dest
    RuleBuilder.testDirCounter = RuleBuilder.testDirCounter + 1
    return self
  def withExistingAndRelativeSourceAndDest(self, tmpdir):
    self.withExistingSourceAndDest(tmpdir)
    self.source = os.path.relpath(self.source)
    self.destination = os.path.relpath(self.destination)
    return self
    
  def build(self):
    return BackupRule(self.title, self.program, self.source,
      self.destination, self.interval)

def anyRule(): return RuleBuilder() 