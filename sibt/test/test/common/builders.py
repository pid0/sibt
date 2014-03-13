from sibt.domain.scheduling import Scheduling
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
    
  def build(self):
    return Scheduling(self.ruleName, self.options)

def anyScheduling(): return SchedulingBuilder().build()

