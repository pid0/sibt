from sibt.infrastructure.exceptions import \
    SynchronizerFuncNotImplementedException, ExternalFailureException
from sibt.domain.port import Port
from sibt.infrastructure import types
from sibt.domain.optioninfo import OptionInfo

class DefaultValueSynchronizer(object):
  def __init__(self, wrapped):
    self._wrapped = wrapped

  def _getAvailableOptions(self):
    try:
      return self._wrapped.availableOptions
    except SynchronizerFuncNotImplementedException:
      return []

  def _locOptionInfosCorrespondingToPorts(self, ports):
    return [OptionInfo("Loc" + str(i + 1), types.Location) for i in 
        range(len(ports))]

  @property
  def availableOptions(self):
    return self._getAvailableOptions() + \
        self._locOptionInfosCorrespondingToPorts(self.ports)

  def versionsOf(self, *args):
    try:
      return self._wrapped.versionsOf(*args)
    except (SynchronizerFuncNotImplementedException, ExternalFailureException):
      return []

  @property
  def ports(self):
    try:
      return self._wrapped.ports
    except SynchronizerFuncNotImplementedException:
      return [Port(["file"], False), Port(["file"], True)]

  @property
  def onePortMustHaveFileProtocol(self):
    try:
      return self._wrapped.onePortMustHaveFileProtocol
    except SynchronizerFuncNotImplementedException:
      return False

  def check(self, *args):
    try:
      return self._wrapped.check(*args)
    except SynchronizerFuncNotImplementedException:
      return []

  def __getattr__(self, name):
    return getattr(self._wrapped, name)
