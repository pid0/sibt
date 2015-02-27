import pytest
from test.common import mock
from sibt.domain.syncrule import SyncRule
from datetime import datetime, timedelta, timezone
from test.common.builders import location, version

class Fixture(object):
  def ruleWith(self, name="some-rule", mockedInterpreter=None, 
      schedOptions={}, interOptions={}):
    if mockedInterpreter is None:
      mockedInterpreter = mock.mock()
      mockedInterpreter.writeLocIndices = []

    interOptions = dict(interOptions)
    if "Loc1" not in interOptions:
      interOptions["Loc1"] = location("/mnt")
    if "Loc2" not in interOptions:
      interOptions["Loc2"] = location("/etc")
    return SyncRule(name, schedOptions, interOptions, False,
        None, mockedInterpreter)

  def mockInter(self):
    ret = mock.mock()
    ret.writeLocIndices = [2]
    return ret

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
  inter = fixture.mockInter()
  interOptions = {
      "Loc1": location("/mnt/data/loc1"), 
      "Loc2": location("/mnt/backup/loc2")}
  rule = fixture.ruleWith(mockedInterpreter=inter, interOptions=interOptions)

  ret = [datetime.now(timezone.utc), 
      datetime.now(timezone.utc) + timedelta(days=1)]
  def check(path, expectedRelativePath, expectedLoc):
    inter.expectCallsInOrder(mock.callMatching("versionsOf", 
        lambda path, locNumber, options: path == expectedRelativePath and 
        locNumber == expectedLoc and options == interOptions,
        ret=ret))
    assert set(rule.versionsOf(path)) == { version(rule, ret[0]),
        version(rule, ret[1]) }
    inter.checkExpectedCalls()

  check(location("/mnt/data/loc1/blah"), "blah", 1)
  check(location("/mnt/backup/loc2/one/two/"), "one/two", 2)
  assert len(rule.versionsOf(location("/mnt/data/quux"))) == 0

def test_shouldProvideAListOfWriteAndNonWriteLocsWithIndicesGivenByInterpreter(
    fixture):
  loc1 = location("/loc1")
  loc2 = location("/loc2")

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

