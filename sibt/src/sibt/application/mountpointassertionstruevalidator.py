import os

from sibt.domain.subvalidators import DiscreteValidator

def _mountPointOf(path):
  ret = path
  while not os.path.ismount(ret):
    ret = os.path.join(ret, "..")
  return os.path.realpath(ret)

class MountPointAssertionsTrueValidator(DiscreteValidator):
  def checkRule(self, rule, unusedRuleSet, errors):
    optionValue = rule.options.get("MustBeMountPoint", None)
    if optionValue is None:
      return

    locNumbers = [int(locNumber) for locNumber in optionValue.split(",")]
    for locNumber in locNumbers:
      path = str(rule.locs[locNumber - 1])
      if not os.path.ismount(path):
        errors.add(("Loc{0} was supposed to be a mount point, but it is "
          "itself mounted at ‘{1}’").format(locNumber, _mountPointOf(path)), 
          rule)
