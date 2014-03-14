import anacron

import pytest

class Fixture(object):
  def __init__(self):
    pass

@pytest.fixture
def fixture():
  return Fixture()

def test_should(fixture):
  assert anacron.x(2) == 4
