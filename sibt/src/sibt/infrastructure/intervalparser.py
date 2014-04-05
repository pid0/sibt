import string
from itertools import dropwhile, takewhile

class SuffixMultipliers(object):
  def __init__(self):
    self.multipliers = {"": 1, "days": 1, "weeks": 7}
  def __getitem__(self, key):
    for suffix in self.multipliers:
      if suffix.startswith(key):
        return self.multipliers[suffix]
    raise Exception("unknown interval unit {0}".format(key))

class IntervalParser(object):
  def parseNumberOfDays(self, src):
    compressed = [c for c in src if c != " "]
    def isDigit(c):
      return c in string.digits
    magnitude, unit = (int("".join(takewhile(isDigit, compressed))),
        "".join(dropwhile(isDigit, compressed)))

    multipliers = SuffixMultipliers()
    magnitude *= multipliers[unit]

    if magnitude <= 0:
      raise Exception("interval must be at least one day")
    
    return magnitude
