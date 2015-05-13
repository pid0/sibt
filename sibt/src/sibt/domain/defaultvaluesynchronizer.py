from sibt.infrastructure.exceptions import \
    SynchronizerFuncNotImplementedException, ExternalFailureException
from sibt.domain.port import Port

class DefaultValueSynchronizer(object):
  def __init__(self, wrapped):
    self.wrapped = wrapped

  @property
  def availableOptions(self):
    try:
      return self.wrapped.availableOptions
    except SynchronizerFuncNotImplementedException:
      return []

  def versionsOf(self, *args):
    try:
      return self.wrapped.versionsOf(*args)
    except (SynchronizerFuncNotImplementedException, ExternalFailureException):
      return []

  @property
  def ports(self):
    try:
      return self.wrapped.ports
    except SynchronizerFuncNotImplementedException:
      return [Port(["file"], False), Port(["file"], True)]

  @property
  def onePortMustHaveFileProtocol(self):
    try:
      return self.wrapped.onePortMustHaveFileProtocol
    except SynchronizerFuncNotImplementedException:
      return False

  def __getattr__(self, name):
    return getattr(self.wrapped, name)
