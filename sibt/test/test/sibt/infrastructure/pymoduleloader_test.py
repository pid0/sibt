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

import pytest
from sibt.infrastructure.pymoduleloader import PyModuleLoader

class Fixture(object):
  def __init__(self, tmpdir):
    self.loader = PyModuleLoader("top")
    self.tmpdir = tmpdir

  def loadModule(self, name, code):
    path = self.tmpdir.join(name)
    path.write(code)
    return self.loader.loadFromFile(str(path), name)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldReturnUsableModule(fixture):
  module = fixture.loadModule("some-module", 
      "def getX(): return 4\n")
  assert module.getX() == 4
