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

from sibt.infrastructure.filesdbexecutionslog import FilesDBExecutionsLog
from sibt.application.configrepo import readRulesIntoFinder, isSysRule, \
    openLogs
from sibt.application.rulesfinder import EmptyRepo, RulesFinder

class _ThinRule(object):
  def __init__(self, name, enabled):
    self.name = name
    self.enabled = enabled

class _ThinRuleFactory(object):
  def readRule(self, name, ruleOptions, schedulerOptions, synchronizerOptions,
      isEnabled):
    return _ThinRule(name, isEnabled)

class TopLevelLogInterface(object):
  def __init__(self, paths, sysPaths):
    self.userLog, self.sysLog = openLogs(paths, sysPaths)

    self.rulesFinder = readRulesIntoFinder(paths, sysPaths, _ThinRuleFactory(),
        _ThinRuleFactory(), lambda rule: True,
        readUserConf=paths is not None,
        readSysConf=sysPaths is not None)

  def executionsOfRules(self, *patterns):
    rules = self.rulesFinder.findRulesByPatterns(patterns, onlySyncRules=False, 
        keepUnloadedRules=True)

    userRuleNames = [rule.name for rule in rules if not isSysRule(rule)]
    sysRuleNames = [rule.name for rule in rules if isSysRule(rule)]

    ret = self.userLog.executionsOfRules(userRuleNames)
    ret.update(self.sysLog.executionsOfRules(sysRuleNames))
    return ret
