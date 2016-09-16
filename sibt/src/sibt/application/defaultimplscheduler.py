class DefaultImplScheduler(object):
  def __init__(self, wrappedScheduler):
    self._wrapped = wrappedScheduler
  
  def execute(self, execEnv, scheduling):
    if hasattr(self._wrapped, "execute"):
      return self._wrapped.execute(execEnv, scheduling)

    return execEnv.runSynchronizer()

  def __getattr__(self, name):
    return getattr(self._wrapped, name)
