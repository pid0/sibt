import pytest

class Fixture(object):
  def __init__(self):
    objectsUnderTest

@pytest.fixture
def fixture():
  return Fixture()

def test_(fixture):
#TODO write files, should copy them to dest
  pass
