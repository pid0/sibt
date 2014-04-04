import pytest
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader

class Fixture(object):
  def __init__(self, tmpdir):
    self.loader = PyModuleSchedulerLoader("top")
    self.tmpdir = tmpdir

  def loadModule(self, name, code, *initArgs):
    path = self.tmpdir.join(name + "foo")
    path.write(code)
    return self.loader.loadFromFile(str(path), name, initArgs)

EmptyInitFunc = "def init(*args): pass"

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldReturnUsableModule(fixture):
  module = fixture.loadModule("some-module", 
      "def getX(): return 4\n" + EmptyInitFunc)
  assert module.getX() == 4

def test_shouldSetNameAttribute(fixture):
  module = fixture.loadModule("foo", EmptyInitFunc)
  module2 = fixture.loadModule("bar", EmptyInitFunc)
  assert module.name == "foo"
  assert module2.name == "bar"

def test_shouldCallInitFunctionAsFinalStep(fixture):
  fixture.loadModule("module", """
from test.sibt.infrastructure import pymoduleschedulerloader_test 
def init(x, y): pymoduleschedulerloader_test.Result = x + y""",
      1, 2)
  assert Result == 3

