import pytest
from test.common import mock
from sibt.domain.syncrule import SyncRule
from datetime import datetime, timedelta, timezone

class Fixture(object):
  def ruleWith(self, mockedInterpreter, schedOptions={}, interOptions={}):
    schedOptions["Name"] = "sched"
    interOptions["Name"] = "inter"
    interOptions["Foo"] = "bar"
    return SyncRule("some-rule", schedOptions, interOptions, False,
        None, mockedInterpreter)

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldReturnVersionsGotFromInterpreterIfFileIsInALocOption(fixture):
  inter = mock.mock()
  inter.writeLocIndices = [2]
  rule = fixture.ruleWith(inter, interOptions={"Loc1": 
      "/mnt/data/loc1", "Loc2": "/mnt/backup/loc2"})

  ret = [datetime.now(timezone.utc), datetime.now(timezone.utc) + 
      timedelta(days=1)]
  def check(path, expectedPath, expectedLoc):
    inter.expectCallsInOrder(mock.callMatching("versionsOf", 
        lambda path, locNumber, options: path == expectedPath and 
        locNumber == expectedLoc and options == rule.interpreterOptions, 
        ret=ret))
    versions = rule.versionsOf(path)
    assert len(versions) == 2
    assert versions[0].rule == rule
    assert versions[0].time == ret[0]
    assert versions[1].time == ret[1]
    assert versions[1].rule == rule
    inter.checkExpectedCalls()

  check("/mnt/data/loc1/blah", "blah", 1)
  check("/mnt/backup/loc2/one/two/", "one/two", 2)
  assert len(rule.versionsOf("/mnt/data/quux")) == 0

def test_shouldProvideACollectionOfWriteLocsWithIndicesSelectedByInterpreter(
    fixture):
  loc1 = "/loc1"
  loc2 = "/loc1"

  def checkWriteLocs(indices, expectedLocs):
    inter = lambda x:x
    inter.writeLocIndices = indices

    rule = fixture.ruleWith(inter, interOptions={"Loc1": loc1,
        "Loc2": loc2})

    assert set(rule.writeLocs) == set(expectedLocs)

  checkWriteLocs([1], [loc1])
  checkWriteLocs([1, 2], [loc1, loc2])

