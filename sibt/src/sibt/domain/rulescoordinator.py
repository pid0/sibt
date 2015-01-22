from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode
from sibt.domain.exceptions import ValidationException

class RulesCoordinator(object):
  def __init__(self, rules):
    self.rules = rules
    self._groups = type(self).SchedulingGroup.divideRules(rules)

  def schedule(self, validator):
    validationErrors = validator.validate(self)
    if len(validationErrors) > 0:
      raise ValidationException(validationErrors)

    for group in self._groups:
      group.scheduler.run(group.schedulings)

  def __iter__(self):
    return iter(self.rules)

  @property
  def schedulerErrors(self):
    ret = []
    for group in self._groups:
      ret += [(group.scheduler.name, error) for error in 
          group.scheduler.check(group.schedulings)]
    return ret

  class SchedulingGroup(CaseClassEqualityHashCode):
    def __init__(self, scheduler, rules):
      self.scheduler = scheduler
      self.rules = frozenset(rules)

    @property
    def schedulings(self):
      return [rule.scheduling for rule in self.rules]

    @classmethod
    def divideRules(clazz, rules):
      schedulers = set(map(lambda rule: rule.scheduler, rules))
      return [clazz(scheduler, filter(lambda rule: rule.scheduler == scheduler, 
        rules)) for scheduler in schedulers]

    def __repr__(self):
      return "SchedulingGroup{0}".format((self.scheduler, self.rules))

