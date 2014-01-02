import pytest
from test.common.mutableclock import MutableClock
from test.common.rulebuilder import anyRule
from datetime import timedelta, datetime, timezone, time
from sibt.infrastructure.intervalbasedrulesfilter import \
 IntervalBasedRulesFilter
from sibt import executiontimeprediction
from sibt.configuration.timerange import TimeRange

class ExecutionTimeRepoMock(object):
  def __init__(self):
    self.dict = dict()
  
  def executionTimeOf(self, rule):
    return self.dict.get(rule.title)
  
  def setExecutionTimeFor(self, rule, time):
    self.dict[rule.title] = time

class Fixture(object):
  def __init__(self):
    self.clock = MutableClock.fromUTCNow()
    self.repo = ExecutionTimeRepoMock()
    self.ruleWithoutInterval = anyRule().withoutInterval().build()
    self.twoDaysRule = anyRule().withInterval(timedelta(days=2)).build()
    self.threeDaysRule = anyRule().withInterval(timedelta(days=3)).build()
    self.threeWeeksRule = anyRule().withInterval(timedelta(weeks=3)).build() 
    self.rules = { 
      self.twoDaysRule, self.threeDaysRule, self.threeWeeksRule,
      self.ruleWithoutInterval }
    self.filter = IntervalBasedRulesFilter(self.repo, self.clock)
  
  def _dueRules(self):
    return self.filter.getDueRules(self.rules)
  dueRules = property(_dueRules)
    
  def setExecutionTimesToClock(self):
    for rule in self.rules:
      self.repo.setExecutionTimeFor(rule, self.clock.time())
    
@pytest.fixture
def fixture():
  return Fixture()

def test_shouldConsiderARuleDueIfItHasNoExecutionTime(fixture):
  assert fixture.dueRules == fixture.rules
  
def test_shouldAlwaysConsiderARuleDueThatHasNoInterval(fixture):
  fixture.setExecutionTimesToClock()
  assert fixture.dueRules == { fixture.ruleWithoutInterval }
  
def test_shouldConsiderARuleDueIffTheIntervalHasPassedSinceExecutionTime(
  fixture):
  fixture.setExecutionTimesToClock()
  
  fixture.clock.putForward(timedelta(days=1))
  assert fixture.dueRules == { fixture.ruleWithoutInterval }
  
  fixture.clock.putForward(timedelta(days=2))
  assert fixture.dueRules == { fixture.ruleWithoutInterval,
    fixture.twoDaysRule, fixture.threeDaysRule }
  
  fixture.clock.putForward(timedelta(days=18))
  assert fixture.dueRules == fixture.rules
  
  twoDaysAgo = fixture.clock.time() - timedelta(days=2) 
  fixture.repo.setExecutionTimeFor(fixture.threeDaysRule, twoDaysAgo)
  assert fixture.threeDaysRule not in fixture.dueRules
  
def test_shouldBeAbleToTellTheTimeWhenARuleIsConsideredDueAgain(fixture):
  fixture.clock.setDateTime(datetime(2010, 5, 20, 11, 35, tzinfo=timezone.utc))
  
  assert (fixture.filter.predictNextExecutionTimeOf(fixture.twoDaysRule) is
    executiontimeprediction.Due)
  
  fixture.setExecutionTimesToClock()
  assert (fixture.filter.predictNextExecutionTimeOf(fixture.twoDaysRule) ==
    datetime(2010, 5, 22, 11, 35, tzinfo=timezone.utc))
  assert (fixture.filter.predictNextExecutionTimeOf(fixture.threeDaysRule) ==
    datetime(2010, 5, 23, 11, 35, tzinfo=timezone.utc))
  
  assert (fixture.filter.predictNextExecutionTimeOf(fixture.ruleWithoutInterval)
    == executiontimeprediction.Due)
  
  fixture.clock.putForward(timedelta(days=2, hours=5))
  assert (fixture.filter.predictNextExecutionTimeOf(fixture.twoDaysRule) is
    executiontimeprediction.Due)
  assert (fixture.filter.predictNextExecutionTimeOf(fixture.threeDaysRule) ==
    datetime(2010, 5, 23, 11, 35, tzinfo=timezone.utc))
  
def test_shouldAddNecessaryOffsetToNextRunTimeIfItFallsWithinACertainTimeRange(
  fixture):
  fixture.clock.setDateTime(datetime(1993, 10, 9, 15, 5, tzinfo=timezone.utc))
  fixture.setExecutionTimesToClock()
  fixture.clock.putForward(timedelta(hours=2))
  
  illegalTimeRange = TimeRange(time(15, 5), time(17, 12))
  
  assert fixture.filter.predictNextExecutionTimeOf(fixture.threeDaysRule,
    illegalTimeRange) == datetime(1993, 10, 12, 17, 13, tzinfo=timezone.utc)
    
  assert fixture.filter.predictNextExecutionTimeOf(fixture.ruleWithoutInterval,
    illegalTimeRange) == datetime(1993, 10, 9, 17, 13, tzinfo=timezone.utc)
    