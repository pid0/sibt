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

from fnmatch import fnmatchcase
from sibt.application.exceptions import RulePatternMismatchException
import itertools
from sibt.configuration.exceptions import MissingConfigValuesException, \
    NotReadableException

class EmptyRepo(object):
  def __init__(self):
    self.enabledNames = []
    self.disabledNames = []
    self.names = []

class RuleNameMatch(object):
  def __init__(self, isDirect, isSysRule, name):
    self.isDirect = isDirect
    self.isSysRule = isSysRule
    self.name = name
  
  def __eq__(self, other):
    return self.name == other.name
  def __hash__(self):
    return hash(self.name)

def _matchNamesAgainstPattern(pattern, enabledNames, disabledNames,
    isSysConfig):
  if pattern in disabledNames or pattern in enabledNames:
    return [RuleNameMatch(True, isSysConfig, pattern)]

  return [RuleNameMatch(False, isSysConfig, name) for name in enabledNames if 
      fnmatchcase(name, pattern)]

class RulesFinder(object):
  def __init__(self, userRules, sysRules, sysRuleFilter):
    self.userRules = userRules
    self.sysRules = sysRules
    self.sysRuleFilter = sysRuleFilter

  def getSyncRule(self, name):
    return self.userRules.getRule(name, keepUnloaded=False)

  def findRulesByPatterns(self, patterns, onlySyncRules, 
      keepUnloadedRules=False):
    userMatchesLists, sysMatchesLists = self._findMatchesInBothRepos(
        onlySyncRules, patterns, not onlySyncRules)
    
    for matches1, matches2, pattern in zip(userMatchesLists, sysMatchesLists, 
        patterns):
      if len(matches1) == 0 and len(matches2) == 0:
        raise RulePatternMismatchException(pattern)

    return list(itertools.chain(
        self._matchesListsToRules(userMatchesLists, keepUnloadedRules), 
        self._matchesListsToRules(sysMatchesLists, keepUnloadedRules)))

  def getAll(self, keepUnloadedRules=False):
    matches = self._findMatchesInBothRepos(False, ["*"], True)
    return list(self._matchesListsToRules(itertools.chain(*matches),
      keepUnloadedRules))

  def _findMatchesInBothRepos(self, onlySyncRules, patterns, 
      matchAgainstDisabled):
    sysRules = EmptyRepo() if onlySyncRules else self.sysRules
    return (
        self._findMatchesInRepo(self.userRules, patterns, matchAgainstDisabled,
          False), 
        self._findMatchesInRepo(sysRules, patterns, matchAgainstDisabled, True))

  def _findMatchesInRepo(self, repo, patterns, matchAgainstDisabled, 
      isSysConfig):
    enabledNames = repo.enabledNames
    disabledNames = repo.disabledNames

    if matchAgainstDisabled:
      enabledNames += disabledNames
      disabledNames = []

    return [_matchNamesAgainstPattern(pattern, enabledNames, 
      disabledNames, isSysConfig) for pattern in patterns]

  def _matchesListsToRules(self, matchesLists, keepUnloadedRules):
    matches = set(_flatten(matchesLists))
    for match in matches:
      try:
        rule = self._findRuleByName(match.name, keepUnloadedRules)
      except MissingConfigValuesException:
        if match.isDirect or self._getUnloadedRule(match.name).enabled:
          raise
        continue
      except NotReadableException:
        if match.isDirect or not match.isSysRule:
          raise
        continue

      if match.isSysRule and not match.isDirect and \
          not self.sysRuleFilter(rule):
        continue
      yield rule

  def _findRuleByName(self, name, keepUnloadedRule):
    repo = self.userRules if name in self.userRules.names else \
        self.sysRules
    return repo.getRule(name, keepUnloadedRule)

  def _getUnloadedRule(self, name):
    repo = self.userRules if name in self.userRules.names else \
        self.sysRules
    return repo.getRuleWithoutLoading(name)

def _flatten(xss):
  return (x for xs in xss for x in xs)
