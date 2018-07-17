import pytest
from datetime import datetime
from test.integration.synchronizers.synchronizertest import \
    RunnableFileSynchronizerTestFixture 

class Fixture(RunnableFileSynchronizerTestFixture):
  def __init__(self, tmpdir):
    super().__init__(tmpdir)
    self.load("null")

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldOutputTheCurrentDateWhenToldToSync(fixture, capfd):
  fixture.syncer.sync(fixture.optsWith({}))
  stdout, _ = capfd.readouterr()

  assert str(datetime.today().year) in stdout

