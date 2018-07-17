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

from sibt.configuration.exceptions import ConfigurableNotFoundException, \
    OptionParseException, ConfigConsistencyException
from sibt.domain import syncrule
from sibt.domain.synchronizeroptions import SynchronizerOptions

def makeException(ruleName, message):
  return ConfigConsistencyException("rule", ruleName, message)

class RuleFromStringOptionsReader(object):
  def __init__(self, ruleFactory, optionsParser, schedulers, synchronizers):
    self.ruleFactory = ruleFactory
    self.schedulers = schedulers
    self.synchronizers = synchronizers
    self.optionsParser = optionsParser

  def readRule(self, ruleName, ruleOptions, schedulerOptions, 
      synchronizerOptions, isEnabled):
    scheduler = self._findByNameOption(self.schedulers, schedulerOptions,
        "scheduler", ruleName)
    synchronizer = self._findByNameOption(self.synchronizers, 
        synchronizerOptions, "synchronizer", ruleName)

    parsedRuleOpts, parsedSchedOpts, parsedSyncerOpts = \
      self._collectingParseErrors(ruleName, 
          ("[Rule]", "[Scheduler]", "[Synchronizer]"),
          lambda: self._parseOptions(syncrule.AvailableOptions, ruleOptions, 
            False), 
          lambda: self._parseOptions(scheduler.availableOptions, 
            schedulerOptions, True), 
          lambda: SynchronizerOptions.fromDict(self._parseOptions(
            synchronizer.availableOptions, synchronizerOptions, True)))

    return self.ruleFactory.build(ruleName, scheduler, synchronizer,
        parsedRuleOpts, parsedSchedOpts, parsedSyncerOpts, isEnabled)

  def _findByNameOption(self, objects, options, searchDescription, ruleName):
    expectedName = self._getNameOrThrowEx(options, searchDescription, ruleName)
    try:
      return objects.getByName(expectedName)
    except ConfigurableNotFoundException as ex:
      ex.unitType = searchDescription
      ex.ruleName = ruleName
      raise 

  def _getNameOrThrowEx(self, options, unitType, ruleName):
    if "Name" not in options:
      raise ConfigurableNotFoundException(None, unitType=unitType, 
          ruleName=ruleName, message="Name option not given")
    return options["Name"]

  def _parseOptions(self, optionInfos, options, removeNameOpt):
    if removeNameOpt:
      del options["Name"]

    return self.optionsParser.parseOptions(optionInfos, options)

  def _collectingParseErrors(self, ruleName, descriptions, *funcs):
    exceptions = []
    ret = []

    for func in funcs:
      try:
        ret.append(func())
        exceptions.append(None)
      except OptionParseException as ex:
        exceptions.append(ex)
    
    if any(ex is not None for ex in exceptions):
      raise makeException(ruleName, "\n".join(desc + " " + str(ex) for 
        desc, ex in zip(descriptions, exceptions) if ex is not None))
    return ret
