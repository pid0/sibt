import pytest
from datetime import datetime
from test.common.builders import anyUTCDateTime
from test.integration.interpreters.interpretertest import \
    InterpreterTestFixture 

class Fixture(InterpreterTestFixture):
  def __init__(self, tmpdir):
    self.load("null", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldHaveDefaultOfNoAvailableOptions(fixture):
  assert fixture.inter.availableOptions == []

def test_shouldOutputTheCurrentDateWhenToldToSync(fixture, capfd):
  fixture.inter.sync(fixture.optsWith({}))
  stdout, _ = capfd.readouterr()

  assert str(datetime.today().year) in stdout

def test_shouldNotFailWhenCalled(fixture):
  fixture.inter.restore("", 1, anyUTCDateTime(), None, fixture.optsWith({}))
  fixture.inter.listFiles("", 1, anyUTCDateTime(), fixture.optsWith({}))
  assert fixture.inter.versionsOf("", 1, fixture.optsWith({})) == []
