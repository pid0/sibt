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

from sibt.domain.syncrule import SyncRule
from sibt.domain import syncrule
from sibt.domain.exceptions import LocationInvalidException
from sibt.configuration.exceptions import ConfigConsistencyException, \
    RuleNameInvalidException
from sibt.configuration.optionvaluesparser import parseLocation
from sibt.domain.syncrule import LocCheckLevel
from sibt.domain.optioninfo import OptionInfo

def makeException(ruleName, message):
  return ConfigConsistencyException("rule", ruleName, message)

class RuleFactory(object):
  def __init__(self, log):
    self.log = log

  def build(self, name, scheduler, synchronizer, ruleOptions, 
      schedulerOptions, synchronizerOptions, enabled):
    self._throwIfRuleNameInvalid(name)

    self._throwIfLocOptionsNotPresent(synchronizerOptions, synchronizer.ports, 
        name)

    self._throwIfUnsupported(scheduler.availableOptions, 
        schedulerOptions, "scheduler", name)
    self._throwIfUnsupported(synchronizer.availableOptions,
        synchronizerOptions, "synchronizer", name)
    self._throwIfUnsupported(syncrule.AvailableOptions, ruleOptions, "rule", 
        name)

    self._setRuleOptionsDefaultValues(ruleOptions)

    return SyncRule(name, ruleOptions, schedulerOptions, synchronizerOptions,
        enabled, scheduler, synchronizer, self.log)

  def _throwIfLocOptionsNotPresent(self, syncerOpts, ports, ruleName):
    if len(syncerOpts.locs) < len(ports):
      raise makeException(ruleName, 
          "does not have minimum options for synchronizer ({0})".format(
            ", ".join("Loc" + str(i + 1) for i in range(len(syncerOpts.locs),
              len(ports)))))

  def _throwIfRuleNameInvalid(self, name):
    if "," in name:
      raise RuleNameInvalidException(name, ",")
    if " " in name:
      raise RuleNameInvalidException(name, " ")

  def _throwIfUnsupported(self, supportedOptionInfos, options, description, 
      ruleName):
    unsupportedOptions = self._unsupportedOptions(supportedOptionInfos, options)
    if len(unsupportedOptions) > 0:
      raise makeException(ruleName, "unsupported {0} options: {1}".format(
          description, ", ".join(unsupportedOptions)))

  def _unsupportedOptions(self, supportedOptionInfos, options):
    supportedNames = [opt.name for opt in supportedOptionInfos]
    return [key for key in options.keys() if key not in supportedNames]

  def _setRuleOptionsDefaultValues(self, options):
    options["AllowedForUsers"] = options.get("AllowedForUsers", "")
    options["LocCheckLevel"] = options.get("LocCheckLevel", 
        LocCheckLevel.Default)
