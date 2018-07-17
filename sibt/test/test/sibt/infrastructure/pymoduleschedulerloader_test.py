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
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from test.common import mock

class Fixture(object):
  def __init__(self):
    self.moduleLoader = mock.mock()
    self.loader = PyModuleSchedulerLoader(self.moduleLoader)
    self.path = "/etc/foo.py"
    self.validModule = lambda x:x
    self.validModule.init = lambda *args: None
    self.validModule.availableOptions = []
    self.validModule.availableSharedOptions = []

  def loadScheduler(self, module, name, initArgs=[]):
    self.moduleLoader.expectCalls(
        mock.call("loadFromFile", (self.path, name), ret=module))
    ret = self.loader.loadFromFile(self.path, name, initArgs)
    self.moduleLoader.checkExpectedCalls()
    return ret

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldReturnSchedulerBasedOnPythonModuleInAFileAndSetItsName(fixture):
  name = "a-sched-module"
  module = fixture.validModule
  module.availableOptions = ["b Foo"]

  loadedSched = fixture.loadScheduler(module, name)
  assert loadedSched.availableOptions[0].name == "Foo"
  assert loadedSched.name == name

def test_shouldCallInitFunctionAsFinalStep(fixture):
  expectedArgs = (1, 2, 3)
  result = [0]
  def initFunc(*args):
    if args == expectedArgs:
      result[0] = 4

  module = fixture.validModule
  module.init = initFunc
  fixture.loadScheduler(module, "module", expectedArgs)
  assert result[0] == 4
