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
import os
from datetime import timedelta, datetime
from sibt.configuration.exceptions import ConfigConsistencyException, \
  RuleNameInvalidException, MissingConfigValuesException
from sibt.infrastructure import collectFilesInDirs
import functools
from sibt.configuration.lazysyncrule import LazySyncRule

RuleSec = "Rule"
SyncerSec = "Synchronizer"
SchedSec = "Scheduler"
AllowedSections = [RuleSec, SyncerSec, SchedSec]

class DirBasedRulesReader(object):
  def __init__(self, confFileReader, rulesDir, enabledDir, factory, namePrefix):
    self.rulesDir = rulesDir
    self.enabledDir = enabledDir
    self.factory = factory
    self.namePrefix = namePrefix
    self.extensionsToIgnore = [".inc"]
    self.confFileReader = confFileReader
    
  def read(self):
    return [rule for instancesList in collectFilesInDirs([self.rulesDir], 
      self._readInstancesFromBaseRule) for rule in instancesList]

  def _readInstancesFromBaseRule(self, baseRulePath, baseRuleName):
    if any(baseRuleName.endswith(extension) for extension in 
        self.extensionsToIgnore):
      return None

    instances =  collectFilesInDirs([self.enabledDir], functools.partial(
      self._buildLazyInstance, baseRulePath, baseRuleName, True))

    if len(instances) == 0:
      disabledRule = self._buildLazyInstance(baseRulePath, baseRuleName, False, 
        baseRulePath, "@" + baseRuleName)
      if disabledRule is not None:
        return [disabledRule]

    return instances

  def _buildLazyInstance(self, baseRulePath, baseRuleName, isEnabled, 
      path, fileName):
    if not fileName.endswith("@" + baseRuleName):
      return None

    variablePart = fileName[:-len("@" + baseRuleName)]
    instanceName = fileName[1:] if fileName.startswith("@") else fileName

    return LazySyncRule(self.namePrefix + instanceName, isEnabled, 
        lambda: self._loadInstance(path, baseRulePath, isEnabled, 
          instanceName, variablePart))

  def _loadInstance(self, path, baseRulePath, isEnabled, instanceName,
      variablePart):
    if instanceName.startswith("+"):
      raise RuleNameInvalidException(instanceName, "+", 
          furtherDescription="at the beginning", file=path)

    sections = self.confFileReader.sectionsFromFiles([baseRulePath] + 
        ([path] if isEnabled else []), 
        variablePart if isEnabled else None)

    try:
      return self.factory.readRule(self.namePrefix + instanceName, 
          sections[RuleSec],
          sections[SchedSec], 
          sections[SyncerSec], isEnabled)
    except ConfigConsistencyException as ex:
      ex.file = path
      raise
