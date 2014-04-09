from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode
from datetime import timezone

TimeFormat = "%Y-%m-%dT%H:%M:%S"
class Version(CaseClassEqualityHashCode):
  def __init__(self, ruleName, time):
    if time.tzinfo is None:
      raise Exception("version must have aware datetime")
    self.ruleName = ruleName
    self.time = time

  def timeAsUTCW3C(self):
    return self.time.astimezone(timezone.utc).strftime(TimeFormat)
  timeAsUTCW3C = property(timeAsUTCW3C)
  def timeAsLocalW3C(self):
    return self.time.astimezone().strftime(TimeFormat)
  timeAsLocalW3C = property(timeAsLocalW3C)
