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

class SchedulingSet(object):
  def __init__(self, schedulings):
    self.schedulings = list(schedulings)
  
  def __iter__(self):
    return iter(self.schedulings)
  def __getitem__(self, index):
    return self.schedulings[index]
  def __len__(self):
    return len(self.schedulings)

  def getSharedOption(self, optionName, defaultValue):
    return self.schedulings[0].options.get(optionName, defaultValue)

  def _checkSchedulingOption(self, checkFunc, scheduling, optionName):
    if optionName not in scheduling.options:
      return None
    return checkFunc(optionName, scheduling.options[optionName], 
        scheduling.ruleName)

  def checkOptionsOfEach(self, checkFunc, *optionNames):
    ret = []
    for scheduling in self.schedulings:
      for optionName in optionNames:
        error = self._checkSchedulingOption(checkFunc, scheduling, optionName)
        if error is not None:
          ret.append(error)
    return ret

  def __repr__(self):
    return "SchedulingSet({0})".format(self.schedulings)
