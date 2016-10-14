import pytest
from test.common import mock
from sibt.domain.syncrule import SyncRule
from datetime import datetime, timedelta, timezone
from test.common.builders import remoteLocation, location, version, port, \
  mockSyncer, mkSyncerOpts, orderedDateTimes, execution, anyUTCDateTime, \
  mockSched
from sibt.domain.exceptions import UnsupportedProtocolException, \
    UnstablePhaseException
from sibt.domain.negativeunstablephasedetector import \
    NegativeUnstablePhaseDetector

class MockExecutionsLog(object):
  def __init__(self):
    self.executions = None
  
  def executionsOfRules(self, ruleNames):
    return dict((name, self.executions) for name in ruleNames)

class PositiveUnstablePhaseDetector(object):
  def isInUnstablePhase(self, ruleToTest):
    return True

def detector():
  return NegativeUnstablePhaseDetector()

def versionsOf(rule, path):
  return rule.versionsOf(path, detector())

class Fixture(object):
  def __init__(self):
    self.log = MockExecutionsLog()

  def ruleWith(self, name="some-rule", scheduler=None,
      mockedSynchronizer=None, schedOptions={}, 
      syncerOptions=mkSyncerOpts()):
    if mockedSynchronizer is None:
      mockedSynchronizer = mockSyncer()

    if "Loc1" not in syncerOptions:
      syncerOptions["Loc1"] = location("/mnt")
    if "Loc2" not in syncerOptions:
      syncerOptions["Loc2"] = location("/etc")
    return SyncRule(name, {}, schedOptions, syncerOptions, 
        False, scheduler, mockedSynchronizer, self.log)

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

def test_shouldReturnVersionsGotFromSynchronizerIfFileIsWithinAPort(fixture):
  syncer = mockSyncer(ports=[port(), port(), port()])
  syncerOptions = mkSyncerOpts(
      Loc1=location("/mnt/data/loc1"), 
      Loc2=location("/mnt/backup/loc2"),
      Loc3=location("/mnt/foo/loc3"))
  rule = fixture.ruleWith(mockedSynchronizer=syncer, 
      syncerOptions=syncerOptions)

  ret = orderedDateTimes(2)
  def check(path, expectedRelativePath, expectedLoc):
    syncer.expectCalls(mock.callMatching("versionsOf", 
        lambda options, path, locNumber: path == expectedRelativePath and
        locNumber == expectedLoc and options == syncerOptions,
        ret=ret))
    assert set(versionsOf(rule, path)) == { version(rule, ret[0]),
        version(rule, ret[1]) }
    syncer.checkExpectedCalls()

  check(location("/mnt/data/loc1/blah"), "blah", 1)
  check(location("/mnt/backup/loc2/one/two/"), "one/two", 2)
  check(location("/mnt/foo/loc3/bar/../"), ".", 3)
  assert len(versionsOf(rule, location("/mnt/data/quux"))) == 0

def test_shouldThrowExceptionIfInUnstablePhaseWhileGettingVersions(fixture):
  syncer = mockSyncer()
  syncer.versionsOf = lambda *_: [anyUTCDateTime()]
  rule = fixture.ruleWith(mockedSynchronizer=syncer, syncerOptions=mkSyncerOpts(
    Loc1=location("/loc1")))
  
  rule.versionsOf(location("/not-in-a-port"), PositiveUnstablePhaseDetector())

  with pytest.raises(UnstablePhaseException):
    rule.versionsOf(location("/loc1"), PositiveUnstablePhaseDetector())

def test_shouldThrowExceptionIfInUnstablePhaseWhenRestoring(fixture):
  rule = fixture.ruleWith(syncerOptions=mkSyncerOpts(Loc1=location("/data")))

  with pytest.raises(UnstablePhaseException):
    rule.restore(location("/data"), version(rule), None, 
        PositiveUnstablePhaseDetector())

def test_shouldDistinguishLocOptionsCorrespondingToPortsThatAreWrittenTo(
    fixture):
  loc1 = location("/loc1")
  loc2 = location("/loc2")

  def checkWriteLocs(writtenToFlags, expectedWriteLocs, expectedNonWriteLocs, 
      loc2=loc2):
    syncer = mockSyncer()
    syncer.ports = [port(isWrittenTo=flag) for flag in writtenToFlags]

    rule = fixture.ruleWith(mockedSynchronizer=syncer, 
        syncerOptions=mkSyncerOpts(Loc1=loc1, Loc2=loc2))

    assert set(rule.writeLocs) == set(expectedWriteLocs)
    assert set(rule.nonWriteLocs) == set(expectedNonWriteLocs)

  checkWriteLocs([True, False], [loc1], [loc2])
  checkWriteLocs([False, True], [loc1], [loc1], loc2=loc1)
  checkWriteLocs([True, True], [loc1, loc2], [])

def test_shouldThrowAnExceptionIfLocOptionsHaveProtocolsNotSupportedBySyncer(
    fixture):
  syncer = mockSyncer()
  syncer.ports = [port(["a", "b"]), port(["c"])]

  fixture.ruleWith(mockedSynchronizer=syncer, 
      syncerOptions=mkSyncerOpts(Loc1=remoteLocation(protocol="b"),
        Loc2=remoteLocation(protocol="c")))

  with pytest.raises(UnsupportedProtocolException) as ex:
    fixture.ruleWith(mockedSynchronizer=syncer, 
        syncerOptions=mkSyncerOpts(Loc1=remoteLocation(protocol="b"),
          Loc2=remoteLocation(protocol="d")))
  assert ex.value.optionName == "Loc2"
  assert ex.value.protocol == "d"
  assert ex.value.supportedProtocols == ["c"]

def test_shouldAssignRestoreTargetToThePortTheFileToBeRestoredWasFoundIn(
    fixture):
  syncer = mockSyncer()
  syncer.ports = [port(["a"]), port(["b"])]
  loc1 = remoteLocation(protocol="a", path="/foo")

  rule = fixture.ruleWith(mockedSynchronizer=syncer,
      syncerOptions=mkSyncerOpts(Loc1=loc1,
        Loc2=remoteLocation(protocol="b", path="/bar")))
 
  with pytest.raises(UnsupportedProtocolException) as ex:
    rule.restore(loc1, version(rule), remoteLocation(protocol="b"), detector())
  assert ex.value.supportedProtocols == ["a"]

def test_shouldEnforceSpecialInvariantThatOnePortMustHaveFileProtocol(fixture):
  syncer = mockSyncer()
  syncer.onePortMustHaveFileProtocol = True
  syncer.ports = [port(["file", "remote"]), port(["file", "remote"])]

  with pytest.raises(UnsupportedProtocolException) as ex:
    fixture.ruleWith(mockedSynchronizer=syncer,
        syncerOptions=mkSyncerOpts(Loc1=remoteLocation(protocol="remote"),
          Loc2=remoteLocation(protocol="remote")))
  assert "at least one" in ex.value.explanation

  rule = fixture.ruleWith(mockedSynchronizer=syncer,
      syncerOptions=mkSyncerOpts(
        Loc1=remoteLocation(protocol="remote", path="/foo"),
        Loc2=remoteLocation(protocol="file", path="/bar")))
  with pytest.raises(UnsupportedProtocolException) as ex:
    rule.restore(remoteLocation(protocol="file", path="/bar/file"),
        version(rule), remoteLocation(protocol="remote"), detector())

def test_shouldReturnItsLastLoggedExecutionIfItExists(fixture):
  firstTime, lastTime = orderedDateTimes(2)
  first, latest = execution(firstTime), execution(lastTime)
  
  fixture.log.executions = [first, latest]
  rule = fixture.ruleWith()
  assert rule.latestExecution == latest

  fixture.log.executions = []
  assert rule.latestExecution is None

def test_shouldBeAbleToPredictItsNextExecutionWithHelpOfTheScheduler(fixture):
  lastEndTime, nextTime = orderedDateTimes(2)
  sched = mockSched()
  def rule():
    return fixture.ruleWith(scheduler=sched)

  fixture.log.executions = [execution(endTime=lastEndTime)]

  sched.expectCalls(mock.callMatching("nextExecutionTime",
    lambda scheduling: scheduling.lastExecutionTime == lastEndTime,
    ret=nextTime))
  nextExecution = rule().nextExecution
  assert not nextExecution.finished
  assert nextExecution.startTime == nextTime

  sched.expectCalls(mock.callMatching("nextExecutionTime", 
    mock.AnyArgs, ret=None))
  assert rule().nextExecution is None

  fixture.log.executions = []
  sched.expectCalls(mock.callMatching("nextExecutionTime", 
    lambda scheduling: scheduling.lastExecutionTime is None, ret=nextTime))
  assert rule().nextExecution.startTime == nextTime

  fixture.log.executions = [execution(unfinished=True)]
  assert rule().nextExecution is None
