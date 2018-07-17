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
