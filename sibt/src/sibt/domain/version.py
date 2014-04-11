from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode
from datetime import timezone

TimeFormat = "%Y-%m-%dT%H:%M:%S"
class Version(CaseClassEqualityHashCode):
  def __init__(self, rule, time):
    if time.tzinfo is None:
      raise Exception("version must have aware datetime")
    self.rule = rule
    self.ruleName = rule.name
    self.time = time

  def strWithUTCW3C(self):
    return self.ruleName + "," + self.time.astimezone(
        timezone.utc).strftime(TimeFormat)
  strWithUTCW3C = property(strWithUTCW3C)
  def strWithLocalW3C(self):
    return self.ruleName + "," + self.time.astimezone().strftime(TimeFormat)
  strWithLocalW3C = property(strWithLocalW3C)
