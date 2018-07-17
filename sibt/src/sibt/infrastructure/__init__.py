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

import os
import os.path

def collectFilesInDirs(dirs, visitor):
  ret = []
  for directory in dirs:
    absDir = os.path.abspath(directory)
    if os.path.isdir(absDir):
      for fileName in os.listdir(absDir):
        path = os.path.join(absDir, fileName)
        if not os.path.isfile(path) or fileName.startswith("."):
          continue
        result = visitor(path, fileName)
        if result is not None:
          ret.append(result)

  return ret
