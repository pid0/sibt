# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
from sibt.domain.syncrule import LocCheckLevel
from sibt.domain.schedulingset import SchedulingSet

def formatLoc(loc):
  return "‘{0}’".format(loc)

class ErrorsList(object):
  def __init__(self):
    self.errors = []

  def add(self, message, *rules):
    self.errors.append(self._errMsg(message, 
      ("‘" + rule.name + "’" for rule in rules)))
  def addWithRuleDescriptions(self, message, *ruleDescriptions):
    self.errors.append(self._errMsg(message, ruleDescriptions))

  def _errMsg(self, message, ruleDescriptions):
    return "in " + ", ".join(ruleDescriptions) + ": " + message

class DiscreteValidator(object):
  def validate(self, ruleSet):
    errorsList = ErrorsList()
    for rule in ruleSet:
      self.checkRule(rule, ruleSet, errorsList)
    return errorsList.errors

class SetsOfTwoValidator(object):
  def validate(self, ruleSet):
    errorsList = ErrorsList()
    ruleList = list(ruleSet)
    for i, rule in enumerate(ruleList):
      for rule2 in ruleList[i+1:]:
        self.checkPair(rule, rule2, errorsList)

    return errorsList.errors

class SynchronizerCheckValidator(DiscreteValidator):
  def checkRule(self, rule, _, errors):
    for syncerCheckError in rule.syncerCheckErrors:
      errors.addWithRuleDescriptions(syncerCheckError, 
          "‘{0}’ (synchronizer ‘{1}’)".format(rule.name, rule.syncerName))
  
class SchedulerCheckValidator(object):
  def validate(self, ruleSet):
    ret = []
    def checkScheduler(scheduler, rules):
      ret.extend(["‘{0}’ reported error: {1}".format(scheduler.name, error) for 
        error in scheduler.check(SchedulingSet(
          rule.scheduling for rule in rules))])
    ruleSet.visitSchedulers(checkScheduler)
    return ret

class AllSharedOptsEqualValidator(object):
  def checkOptsOfSched(self, sched, rulesOfSched):
    ret = []
    for option in (opt.name for opt in sched.availableSharedOptions):
      values = set()
      for rule in rulesOfSched:
        values.add(rule.schedulerOptions.get(option, ""))
      if len(values) > 1:
        ret.append("Values of ‘{0}’ of scheduler ‘{1}’ differ: {2}".format(
          option, sched.name, ", ".join("‘{0}’".format(value) for value 
            in values)))
    return None if len(ret) == 0 else ret 

  def validate(self, ruleSet):
    ret = ruleSet.visitSchedulers(self.checkOptsOfSched)
    return [] if ret is None else ret

class LocExistenceValidator(DiscreteValidator):
  def checkRule(self, rule, ruleSet, errors):
    if rule.options["LocCheckLevel"] == LocCheckLevel.None_:
      return
    for loc in rule.locs:
      if loc.isAFile:
        errors.add(formatLoc(loc) + " is file, should be a folder", rule)
      if not loc.existsAsADir:
        errors.add(formatLoc(loc) + " does not exist", rule)

class LocNotEmptyValidator(DiscreteValidator):
  def checkRule(self, rule, ruleSet, errors):
    if rule.options["LocCheckLevel"] != LocCheckLevel.Strict:
      return
    for loc in rule.locs:
      if loc.isEmpty:
        errors.add(formatLoc(loc) + " is empty", rule)

class NoOverlappingWritesValidator(SetsOfTwoValidator):
  def checkPair(self, rule1, rule2, errors):
    for writeLoc1 in rule1.writeLocs:
      for writeLoc2 in rule2.writeLocs:
        if writeLoc2.contains(writeLoc1) or writeLoc1.contains(writeLoc2):
          errors.add(formatLoc(writeLoc1) + ", " + 
            formatLoc(writeLoc2) + ": overlapping writes", rule1, rule2)

class NoSourceDirOverwriteValidator(DiscreteValidator):
  def checkRule(self, rule, ruleSet, errors):
    for nonWriteLoc in rule.nonWriteLocs:
      for writeLoc in rule.writeLocs:
        if writeLoc.contains(nonWriteLoc):
          errors.add(formatLoc(nonWriteLoc) + " is within " + 
              formatLoc(writeLoc), rule)
