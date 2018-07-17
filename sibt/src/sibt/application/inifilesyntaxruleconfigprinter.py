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

import itertools
from sibt.infrastructure.types import Enum
from datetime import timedelta

class IniFileSyntaxRuleConfigPrinter(object):
  def __init__(self, output):
    self.output = output

  def show(self, rule):
    self.output.println("[Rule]")
    self._printOptions(rule.options)

    self.output.println("")
    self.output.println("[Scheduler]")
    self._printOptions({"Name": rule.scheduler.name}, rule.schedulerOptions)

    self.output.println("")
    self.output.println("[Synchronizer]")
    self._printOptions({"Name": rule.synchronizer.name},
        rule.synchronizerOptions)

  def _printOptions(self, *optionss):
    for options in optionss:
      for optionKey, optionValue in options.items():
        self.output.println("{0} = {1}".format(optionKey, 
          self._formatValue(optionValue)))

  def _formatValue(self, value):
    if isinstance(value, Enum.Value):
      return value.name

    if isinstance(value, bool):
      return "Yes" if value else "No"

    if isinstance(value, timedelta):
      return self._formatTimeDelta(value)

    return str(value)

  def _formatTimeDelta(self, value):
    ret = ""
    unitAndNames = [(timedelta(**{unitName + "s": 1}), unitName) for unitName in
        ["week", "day", "minute", "second"]]

    for unit, unitName in unitAndNames:
      number = int(value / unit)
      if number > 0:
        value = value - (number * unit)
        ret += "{0} {1}{2} ".format(number, unitName, "s" if number > 1 else "")

    return ret if len(ret) > 0 else "0 seconds"
