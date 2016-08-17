class CachingSynchronizer(object):
  def __init__(self, wrapped):
    self._wrapped = wrapped
    self._cachedAttributes = {}

  def _getCachedAttribute(self, name):
    if name not in self._cachedAttributes:
      self._cachedAttributes[name] = getattr(self._wrapped, name)
    return self._cachedAttributes[name]

  def __getattr__(self, name):
    return self._getCachedAttribute(name)
