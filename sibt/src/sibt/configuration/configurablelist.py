from sibt.configuration.exceptions import ConfigurableNotFoundException

class LazyConfigurable(object):
  def __init__(self, name, loadFunc):
    self.name = name
    self._loadFunc = loadFunc

  def load(self):
    return self._loadFunc()

NotFound = object()

class ConfigurableList(object):
  def __init__(self, configurables):
    self._configurables = dict((configurable.name, configurable) for 
        configurable in configurables)
    self._loadedConfigurables = dict()

  def _load(self, configurable):
    if configurable.name in self._loadedConfigurables:
      return

    loaded = configurable
    if hasattr(configurable, "load"):
      loaded = configurable.load()
    self._loadedConfigurables[configurable.name] = loaded

  def __iter__(self):
    for unloaded in self._configurables.values():
      self._load(unloaded)
    return iter(self._loadedConfigurables.values())
  
  def getByName(self, name):
    unloaded = self._configurables.get(name, NotFound)
    if unloaded is NotFound:
      raise ConfigurableNotFoundException(name)

    self._load(unloaded)
    ret = self._loadedConfigurables[name]

    if ret is None:
      raise ConfigurableNotFoundException(name)
    return ret
