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

import os.path

class Paths(object):
  def __init__(self, basePaths):
    self.varDir = basePaths.varDir
    self.readonlyDir = basePaths.readonlyDir
    self.configDir = basePaths.configDir

  @property
  def rulesDir(self):
    return os.path.join(self.configDir, "rules")
  @property
  def synchronizersDir(self):
    return os.path.join(self.configDir, "synchronizers")
  @property
  def schedulersDir(self):
    return os.path.join(self.configDir, "schedulers")
  @property
  def enabledDir(self):
    return os.path.join(self.configDir, "enabled")
  @property
  def logDir(self):
    return os.path.join(self.varDir, "log")
  @property
  def lockDir(self):
    return os.path.join(self.varDir, "locks")
  @property
  def readonlySchedulersDir(self):
    return os.path.join(self.readonlyDir, "schedulers")
  @property
  def readonlySynchronizersDir(self):
    return os.path.join(self.readonlyDir, "synchronizers")
  @property
  def readonlyIncludesDir(self):
    return os.path.join(self.readonlyDir, "include")
  @property
  def runnersDir(self):
    return os.path.join(self.readonlyDir, "runners")

