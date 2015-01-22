import pytest
from test.common import mock
from sibt.domain.syncrule import SyncRule
from datetime import datetime, timedelta, timezone

class Fixture(object):
  def ruleWith(self, name="some-rule", mockedInterpreter=None, 
      schedOptions={}, interOptions={}):
    if mockedInterpreter is None:
      mockedInterpreter = mock.mock()
      mockedInterpreter.writeLocIndices = []
    schedOptions["Name"] = "sched"
    interOptions["Name"] = "inter"
    interOptions["Foo"] = "bar"
    if "Loc1" not in interOptions:
      interOptions["Loc1"] = "/mnt"
    if "Loc2" not in interOptions:
      interOptions["Loc2"] = "/etc"
    return SyncRule(name, schedOptions, interOptions, False,
        None, mockedInterpreter)

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldBeIdentifiedByItsName(fixture):
  rule1, rule2, rule3 = fixture.ruleWith(name="foo"), \
    fixture.ruleWith(name="foo"), fixture.ruleWith(name="bar")

  assert rule1 == rule2
  assert rule2 == rule1
  assert rule2 != rule3
  assert rule1 != rule3

  assert hash(rule1) == hash(rule2)

def test_shouldReturnVersionsGotFromInterpreterIfFileIsInALocOption(fixture):
  inter = mock.mock()
  inter.writeLocIndices = [2]
  rule = fixture.ruleWith(mockedInterpreter=inter, 
      interOptions={"Loc1": "/mnt/data/loc1", "Loc2": "/mnt/backup/loc2"})

  ret = [datetime.now(timezone.utc), datetime.now(timezone.utc) + 
      timedelta(days=1)]
  def check(path, expectedRelativePath, expectedLoc):
    inter.expectCallsInOrder(mock.callMatching("versionsOf", 
        lambda path, locNumber, options: path == expectedRelativePath and 
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

def test_shouldProvideAListOfWriteAndNonWriteLocsWithIndicesGivenByInterpreter(
    fixture):
  loc1 = "/loc1"
  loc2 = "/loc2"

  def checkWriteLocs(indices, expectedWriteLocs, expectedNonWriteLocs, 
      loc2=loc2):
    inter = lambda x:x
    inter.writeLocIndices = indices

    rule = fixture.ruleWith(mockedInterpreter=inter, interOptions={"Loc1": loc1,
        "Loc2": loc2})

    assert set(rule.writeLocs) == set(expectedWriteLocs)
    assert set(rule.nonWriteLocs) == set(expectedNonWriteLocs)

  checkWriteLocs([1], [loc1], [loc2])
  checkWriteLocs([2], [loc1], [loc1], loc2=loc1)
  checkWriteLocs([1, 2], [loc1, loc2], [])

