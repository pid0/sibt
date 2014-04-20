from sibt.infrastructure.interpreterfuncnotimplementedexception import \
    InterpreterFuncNotImplementedException

class DefaultValueInterpreter(object):
  def __init__(self, wrapped):
    self.wrapped = wrapped

  def writeLocIndices(self):
    try:
      return self.wrapped.writeLocIndices
    except InterpreterFuncNotImplementedException:
      return [2]
  writeLocIndices = property(writeLocIndices)

  def __getattr__(self, name):
    return getattr(self.wrapped, name)
