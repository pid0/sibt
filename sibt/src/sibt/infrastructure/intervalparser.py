import string
from itertools import dropwhile, takewhile

class IntervalParser(object):
  def parseNumberOfDays(self, src):
    compressed = [c for c in src if c != " "]
    def isDigit(c):
      return c in string.digits
    magnitude, unit = (int("".join(takewhile(isDigit, compressed))),
        "".join(dropwhile(isDigit, compressed)))

    multipliers = {"": 1, "d": 1, "w": 7}
    if unit in multipliers:
      magnitude *= multipliers[unit]
    else:
      raise Exception("unknown interval unit")
    
    return magnitude
