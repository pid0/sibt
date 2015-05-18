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

  module = lambda x:x
  module.init = initFunc
  fixture.loadScheduler(module, "module", expectedArgs)
  assert result[0] == 4
