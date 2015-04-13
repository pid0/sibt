import pytest
from datetime import datetime
from test.integration.synchronizers.synchronizertest import \
    SynchronizerTestFixture 

class Fixture(SynchronizerTestFixture):
  def __init__(self, tmpdir):
    self.load("null", tmpdir)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldOutputTheCurrentDateWhenToldToSync(fixture, capfd):
  fixture.syncer.sync(fixture.optsWith({}))
  stdout, _ = capfd.readouterr()

  assert str(datetime.today().year) in stdout

