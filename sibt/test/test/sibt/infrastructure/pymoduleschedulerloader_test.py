import pytest
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader

class Fixture(object):
  def __init__(self, tmpdir):
    self.loader = PyModuleSchedulerLoader("top")
    self.tmpdir = tmpdir

  def loadModule(self, name, code):
    path = self.tmpdir.join(name)
    path.write(code)
    return self.loader.loadFromFile(str(path), name)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldReturnUsableModule(fixture):
  module = fixture.loadModule("some-module", "def getX(): return 4")
  assert module.getX() == 4

def test_shouldSetNameAttribute(fixture):
  module = fixture.loadModule("foo", "")
  module2 = fixture.loadModule("bar", "")
  assert module.name == "foo"
  assert module2.name == "bar"
