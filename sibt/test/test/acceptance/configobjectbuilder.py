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

class ConfigObjectBuilder(object):
  testCounter = 0

  def __init__(self, paths, sysPaths, foldersWriter, name, kwParams):
    self.paths = paths
    self.sysPaths = sysPaths
    self.name = name
    self.kwParams = kwParams
    self.foldersWriter = foldersWriter

  def _withParams(self, **kwargs):
    newParams = dict(self.kwParams)
    for key in kwargs:
      newParams[key] = kwargs[key]
    return self.newBasic(self.paths, self.sysPaths, self.foldersWriter, 
        self.name, newParams)

  def withContent(self, newContent):
    return self._withParams(content=newContent)

  def withAnyName(self):
    ConfigObjectBuilder.testCounter += 1
    return self.withName("any-" + str(ConfigObjectBuilder.testCounter))

  def withName(self, newName):
    return self.newBasic(self.paths, self.sysPaths, self.foldersWriter, 
        newName, dict(self.kwParams))

  def asSysConfig(self, isSysConfig=True):
    return self._withParams(isSysConfig=isSysConfig)

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    pass

  @property
  def content(self):
    return self.kwParams["content"]
  @property
  def configuredPaths(self):
    isSysConfig = self.kwParams.get("isSysConfig", False)
    if isSysConfig:
      return self.sysPaths
    else:
      return self.paths
