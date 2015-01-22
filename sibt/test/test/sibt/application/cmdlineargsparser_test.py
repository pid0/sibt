import pytest
from sibt.application.cmdlineargsparser import CmdLineArgsParser

class Fixture(object):
  def __init__(self):
    self.parser = CmdLineArgsParser()

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldBeAbleToRetainCommandLineWordsThatDetermineGlobalOptions(
    fixture):
  words1 = ["--config-dir", "foo"]
  words2 = ["--utc"]
  args = fixture.parser.parseArgs(words1 + words2 + ["schedule", "*"])

  assert len(args.globalOptionsArgs) == len(words1) + len(words2)
  assert args.globalOptionsArgs[args.globalOptionsArgs.
      index(words1[0]) + 1] == words1[1]
  assert words2[0] in args.globalOptionsArgs

