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

from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from sibt.application.paths import Paths
from test.common.mockedbasepaths import MockedBasePaths

def pathsIn(containerLocalPath, readonlyDir=None):
  return Paths(MockedBasePaths(str(containerLocalPath.join("var")),
    str(containerLocalPath.join("config")), str(readonlyDir) if \
    readonlyDir is not None else str(containerLocalPath.join("read-only"))))

def existingPaths(paths):
  DirTreeNormalizer(paths).createNotExistingDirs()
  return paths
