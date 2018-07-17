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

import pickle
import textwrap
import subprocess
import sys

class InterProcessTestFixture(object):
  def __init__(self, moduleName, tmpDirPath, modulesToImport=[]):
    self.moduleName = moduleName
    self.tmpDirPath = tmpDirPath
    self.modulesToImport = ["sys", "pickle"] + modulesToImport
  
  def startInNewProcess(self, code):
    fullCode = r"""
      import {0}
      from {1} import Fixture
      def compute(fixture):
        {2}
      
      fixture = Fixture(sys.argv[1])
      pickle.dump(compute(fixture), sys.stdout.buffer)"""
    fullCode = textwrap.dedent(fullCode).format(
        ", ".join(self.modulesToImport),
        self.moduleName, textwrap.indent(textwrap.dedent(code), "  "))

    return subprocess.Popen([sys.executable, "-c", fullCode, 
      self.tmpDirPath], stdout=subprocess.PIPE)

  def inNewProcess(self, code):
    stdout, _ = self.startInNewProcess(code).communicate()
    return pickle.loads(stdout)
