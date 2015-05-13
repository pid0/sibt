from sibt.domain.syncrule import SyncRule
import os
from datetime import timedelta, datetime
from sibt.configuration.exceptions import ConfigConsistencyException, \
  RuleNameInvalidException, MissingConfigValuesException
from sibt.infrastructure import collectFilesInDirs
import functools

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
      self._buildRuleInstance, baseRulePath, baseRuleName, True))

    if len(instances) == 0:
      disabledRule = self._buildRuleInstance(baseRulePath, baseRuleName, False, 
        baseRulePath, "@" + baseRuleName)
      if disabledRule is not None:
        return [disabledRule]

    return instances

  def _buildRuleInstance(self, baseRulePath, baseRuleName, isEnabled, 
      path, fileName):
    if not fileName.endswith("@" + baseRuleName):
      return None

    variablePart = fileName[:-len("@" + baseRuleName)]
    instanceName = fileName[1:] if fileName.startswith("@") else fileName

    if instanceName.startswith("+"):
      raise RuleNameInvalidException(instanceName, "+", 
          furtherDescription="at the beginning")

    try:
      sections = self.confFileReader.sectionsFromFiles([baseRulePath] + 
          ([path] if isEnabled else []), 
          variablePart if isEnabled else None)
    except MissingConfigValuesException as ex:
      if not isEnabled:
        return None 
      raise

    try:
      return self.factory.build(self.namePrefix + instanceName, 
          sections[RuleSec],
          sections[SchedSec], 
          sections[SyncerSec], isEnabled)
    except ConfigConsistencyException as ex:
      ex.file = path
      raise

