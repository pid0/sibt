from sibt.configuration.configdirreader import ConfigDirReader
from sibt.configuration.backuprule import BackupRule
from test.common.rulebuilder import anyRule
import pytest
from datetime import timedelta, time
from test.common.configurationbuilder import anyConfig, emptyConfig
from sibt.configuration.timerange import TimeRange
from sibt.configuration.configparseexception import ConfigParseException
  
class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    
  def writeRuleFile(self, name, contents):
    self.tmpdir.join(name).write(contents)
    
  def _createReader(self):
    return ConfigDirReader(str(self.tmpdir))  
  def read(self):
    return self._createReader().read()
  def resultShouldBe(self, expectedConfiguration):
    reader = self._createReader()
    assert reader.read() == expectedConfiguration
    
@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)
  
def test_shouldParseThreeRuleAttributesFromEachFileInConfigDirectory(fixture):
  fixture.writeRuleFile("configFile1", """some-tool
  /from/here
  
  /to/there
  
  """)
  fixture.writeRuleFile("configFile2", """
     other-tool
  /from/one
  
  /to/another-place
  
  """)
  
  fixture.resultShouldBe(anyConfig().withRules({anyRule().
    withTitle("configFile1"). 
    withProgram("some-tool").
    withSource("/from/here").
    withDest("/to/there"),
    anyRule().
    withTitle("configFile2").
    withProgram("other-tool").
    withSource("/from/one").
    withDest("/to/another-place")}).build())
  
def test_shouldIgnoreFilesWhoseNamesArePrefixedWithACapitalN(fixture):
  fixture.writeRuleFile("n-active", """a-tool
  /one
  /two
  """)
  fixture.writeRuleFile("Nignore-this", """
  second-tool
  /three
  /four
  """)
  
  fixture.resultShouldBe(anyConfig().withRules({anyRule().
    withTitle("n-active").
    withProgram("a-tool").
    withSource("/one").
    withDest("/two")}).build())
  
def test_shouldParseGlobalConfTimeOfDayRestrictionContentIfExisting(fixture):
  fixture.writeRuleFile("global.conf", """
  
  avoid time of day from 5:00   to  13:15 """)
  
  fixture.resultShouldBe(emptyConfig().withTimeOfDayRestriction(
    TimeRange(time(5, 0), time(13, 15))).build())
  
  
  fixture.writeRuleFile("global.conf", """
  avoid time of day from 4:12 to 8:2 """)
  
  fixture.resultShouldBe(emptyConfig().withTimeOfDayRestriction(
    TimeRange(time(4, 12), time(8, 2))).build())
  
def test_shouldInterpretLastLineAsIntervalOfRule(fixture):
  fixture.writeRuleFile("every-10-days", """program
  /src
  /dest
  every 10d
  """)
  fixture.writeRuleFile("every-4-weeks", """program2
  /src
  /dest
   every   4w
  """)

  fixture.resultShouldBe(anyConfig().withRules(
    {anyRule().
      withTitle("every-10-days").
      withProgram("program").
      withSource("/src").
      withDest("/dest").
      withInterval(timedelta(days=10)),
     anyRule().
      withTitle("every-4-weeks").
      withProgram("program2").
      withSource("/src").
      withDest("/dest").
      withInterval(timedelta(weeks=4))}).build())
  
def test_shouldRaiseExceptionWhenReadingInvalidIntervalTimeUnit(fixture):
  fixture.writeRuleFile("invalid", """
  tool
  /something
  /2
  every 2f
  """)
  
  with pytest.raises(ConfigParseException):
    fixture.read()
    
def test_shouldRaiseExceptionWhenRecognizingFormatErrorInIntervalSpecification(
  fixture):
  fixture.writeRuleFile("invalid", """
  tool
  /1
  /2
  every ad
  """)
  
  with pytest.raises(ConfigParseException):
    fixture.read()
    
def test_shouldRaiseExceptionWhenReadingNegativeInterval(fixture):
  fixture.writeRuleFile("negative-interval", """
  tool
  /1
  /2
  every -2w
  """)
  
  with pytest.raises(ConfigParseException):
    fixture.read()
    
def test_shouldRaiseExceptionWhenEncounteringInvalidGlobalConfFormat(fixture):
  fixture.writeRuleFile("global.conf", "avoid time of day from 4:00 to")
  
  with pytest.raises(ConfigParseException):
    fixture.read()
    
  fixture.writeRuleFile("global.conf", "avoid time of day from 4:00")
  
  with pytest.raises(ConfigParseException):
    fixture.read()
    
def test_shouldRaiseExceptionIfRuleFileHasMoreThanFourNonEmptyLines(fixture):
  fixture.writeRuleFile("invalid", """
  some-tool
  /1
  /2
  every 2d
  
    more on this line
  """)
  
  with pytest.raises(ConfigParseException):
    fixture.read()