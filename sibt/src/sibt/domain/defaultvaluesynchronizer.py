from sibt.infrastructure.exceptions import \
    SynchronizerFuncNotImplementedException
from sibt.domain.port import Port

class DefaultValueSynchronizer(object):
  def __init__(self, wrapped):
    self.wrapped = wrapped

  @property
  def writeLocIndices(self):
    try:
      return self.wrapped.writeLocIndices
    except SynchronizerFuncNotImplementedException:
      return [2]

  @property
  def availableOptions(self):
    try:
      return self.wrapped.availableOptions
    except SynchronizerFuncNotImplementedException:
      return []

  def versionsOf(self, *args):
    try:
      return self.wrapped.versionsOf(*args)
    except SynchronizerFuncNotImplementedException:
      return []

  @property
  def ports(self):
    try:
      return self.wrapped.ports
    except SynchronizerFuncNotImplementedException:
      return [Port(["file"], False), Port(["file"], True)]

  def __getattr__(self, name):
    return getattr(self.wrapped, name)
