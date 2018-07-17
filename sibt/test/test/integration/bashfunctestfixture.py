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

import subprocess
import sys

class BashFuncFailedException(Exception):
  def __init__(self, stderr):
    self.stderr = stderr

class BashFuncTestFixture(object):
  def __init__(self, libraryFilePath, libraryArguments=""):
    self.libraryFilePath = libraryFilePath
    self.libraryArguments = libraryArguments
  
  def compute(self, code, input=None):
    with subprocess.Popen(["bash", "-c", 
      "source '{0}' {1}\n".format(self.libraryFilePath, 
        self.libraryArguments) + code], 
      stderr=subprocess.PIPE, stdout=subprocess.PIPE,
      stdin=subprocess.PIPE) as process:
      stdout, stderr = process.communicate(input)

    sys.stderr.write(stderr.decode())
    if process.returncode != 0:
      raise BashFuncFailedException(stderr)

    return stdout
