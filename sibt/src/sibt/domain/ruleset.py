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

from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode
from sibt.domain.exceptions import ValidationException, RuleExecutingException
from sibt.domain.schedulingset import SchedulingSet

class RuleSet(object):
  def __init__(self, rules):
    self.rules = rules
    self._groups = type(self).SchedulingGroup.divideRules(rules)

  def schedule(self, validator):
    validationErrors = validator.validate(self)
    if len(validationErrors) > 0:
      raise ValidationException(validationErrors)

    for group in self._groups:
      group.throwIfRuleIsExecuting()
      group.scheduler.schedule(group.schedulingSet)

  def __iter__(self):
    return iter(self.rules)

  def visitSchedulers(self, visitor):
    for group in self._groups:
      ret = visitor(group.scheduler, group.rules)
      if ret is not None:
        return ret

  class SchedulingGroup(CaseClassEqualityHashCode):
    def __init__(self, scheduler, rules):
      self.scheduler = scheduler
      self.rules = frozenset(rules)

    def throwIfRuleIsExecuting(self):
      for rule in self.rules:
        if rule.executing:
          raise RuleExecutingException(rule)

    @property
    def schedulingSet(self):
      return SchedulingSet(rule.scheduling for rule in self.rules)

    @classmethod
    def divideRules(clazz, rules):
      schedulers = set(map(lambda rule: rule.scheduler, rules))
      return [clazz(scheduler, filter(lambda rule: rule.scheduler == scheduler, 
        rules)) for scheduler in schedulers]

    def __repr__(self):
      return "SchedulingGroup{0}".format((self.scheduler, self.rules))

