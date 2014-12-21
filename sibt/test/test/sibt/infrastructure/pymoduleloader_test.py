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
