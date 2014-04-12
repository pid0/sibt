from sibt.domain.scheduling import Scheduling
from sibt.application.runner import Runner
from random import random
import os.path

def randstring():
  return str(random())[2:] 
  
def withRandstring(string):
  return string + randstring()

class SchedulingBuilder(object):
  def __init__(self):
    self.ruleName = withRandstring("any-rule")
    self.options = dict()

  def withRuleName(self, name):
    self.ruleName = name
    return self

  def withOption(self, key, value):
    self.options[key] = value
    return self
    
  def build(self):
    return Scheduling(self.ruleName, self.options)

def anyScheduling(): return SchedulingBuilder().build()
def scheduling(): return SchedulingBuilder()
def existingRunner(tmpdir, name): 
  path = tmpdir.join(name)
  path.write("#!/bin/sh")
  return str(path), Runner(name, str(path))

