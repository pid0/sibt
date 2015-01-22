from sibt.domain.scheduling import Scheduling
from sibt.application.runner import Runner
from datetime import datetime, timezone, timedelta
from random import random
import os.path
from test.common import mock

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

def anyUTCDateTime():
  return datetime.now(timezone.utc) - timedelta(days=330)

def mockRuleSet(rules, schedulerErrors=[]):
  class Ret(object):
    def __iter__(self):
      for rule in rules:
        yield rule

  ret = Ret()
  ret.schedulerErrors = schedulerErrors

  return ret

def mockRule(name, scheduler=None, loc1="", loc2="", writeLocs=[2]):
  ret = mock.mock(name)
  ret.name = name
  ret.scheduler = scheduler
  ret.scheduling = object()
  ret.locs = [str(loc1), str(loc2)]
  ret.writeLocs = [str(loc1)] if 1 in writeLocs else [] + \
      [str(loc2)] if 2 in writeLocs else []
  ret.nonWriteLocs = [str(loc1)] if 1 not in writeLocs else [] + \
      [str(loc2)] if 2 not in writeLocs else []
  return ret
