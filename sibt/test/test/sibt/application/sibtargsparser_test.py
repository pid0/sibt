import pytest
from sibt.application.sibtargsparser import SibtArgsParser
from test.common.assertutil import iterToTest
from test.common.bufferingoutput import BufferingOutput

class Fixture(object):
  def __init__(self):
    self.parser = SibtArgsParser()

  def parseArgs(self, args):
    _, result = self.parser.parseArgs(args, BufferingOutput(), 
        BufferingOutput())
    return result

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldBeAbleToRetainCommandLineWordsThatDetermineGlobalOptions(
    fixture):
  words1 = ["--config-dir", "foo"]
  words2 = ["--utc"]
  args = fixture.parseArgs(words1 + words2 + ["schedule", "*"])

  assert args.globalOptionsArgs == words1 + words2 or \
      args.globalOptionsArgs == words2 + words1

def test_shouldDefaultToListingRules(fixture):
  result = fixture.parseArgs([])
  assert result.action == "list"
  assert result.options["command2"] == "rules"

def test_shouldAllowForListingShortcuts(fixture):
  def assertListAction(result):
    assert result.action == "list"
    assert result.options["command2"] == "rules"

  result = fixture.parseArgs(["ls", "-f"])
  assertListAction(result)
  assert result.options["full"] == True
  assert result.options["rule-patterns"] == []

  result = fixture.parseArgs(["li", "foo", "bar"])
  assertListAction(result)
  assert result.options["full"] == False
  assert result.options["rule-patterns"] == ["foo", "bar"]
