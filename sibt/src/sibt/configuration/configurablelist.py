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
