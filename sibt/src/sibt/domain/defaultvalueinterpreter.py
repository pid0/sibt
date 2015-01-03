from sibt.infrastructure.interpreterfuncnotimplementedexception import \
    InterpreterFuncNotImplementedException

class DefaultValueInterpreter(object):
  def __init__(self, wrapped):
    self.wrapped = wrapped

  @property
  def writeLocIndices(self):
    try:
      return self.wrapped.writeLocIndices
    except InterpreterFuncNotImplementedException:
      return [2]

  @property
  def availableOptions(self):
    try:
      return self.wrapped.availableOptions
    except InterpreterFuncNotImplementedException:
      return []

  def versionsOf(self, *args):
    try:
      return self.wrapped.versionsOf(*args)
    except InterpreterFuncNotImplementedException:
      return []

  def __getattr__(self, name):
    return getattr(self.wrapped, name)
