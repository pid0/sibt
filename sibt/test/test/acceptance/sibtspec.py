from test.acceptance.runresult import RunResult
from test.acceptance.bufferingoutput import BufferingOutput
from test.common.executionlogger import ExecutionLogger
import main
import pytest
import os
from datetime import datetime, timezone, timedelta, time
from test.common.constantclock import ConstantClock

class SibtSpecFixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.configDir = tmpdir.mkdir("config")
    self.varDir = tmpdir.mkdir("var")
    self.initialTime = datetime.now(timezone.utc)
    self.time = self.initialTime
    self.timeOfDay = time()
    self.testDirNumber = 0
    
  def removeConfFile(self, name):
    self.configDir.join(name).remove()
  def removeGlobalConf(self):
    self.removeConfFile("global.conf")
  def _writeConfigFile(self, name, contents):
    self.configDir.join(name).write(contents)
  def writeGlobalConf(self, contents):
    self._writeConfigFile("global.conf", contents)
  def writeRuleFile(self, name, contents):
    self._writeConfigFile(name, contents)
  def writeSomeRsyncRule(self, title, interval=""): 
    srcDir = self.newTestDir()
    destDir = self.newTestDir()
    self.writeRuleFile(title, """
    rsync
    {0}
    {1}
    {2}
    """.format(srcDir, destDir, interval))
    return rsyncRun(srcDir + "/", destDir)
  
  def makeNumberOfTestDirs(self, number):
    return tuple((self.newTestDir() for _ in range(number)))
  def newTestDir(self, name=None):
    self.testDirNumber = self.testDirNumber + 1
    tmpDir = str(self.tmpdir)
    parentName = os.path.join(tmpDir, "testdir-" + str(self.testDirNumber))
    fullName = parentName if name is None else os.path.join(parentName, name)
    
    os.makedirs(fullName)
    return fullName
    
  def sibtShouldNotExecuteAnyPrograms(self):
    assert self.result.executionLogger.programsList == []
  def sibtShouldAmongOthersExecute(self, expected):
    assert expected in self.result.executionLogger.programsList
  def sibtShouldExecute(self, expected):
    assert self.result.executionLogger.programsList == expected
  def sibtShouldExecuteInAnyOrder(self, expected):
    assert set(self.result.executionLogger.programsList) == set(expected)
  
  def outputShouldBeEmpty(self):
    self.outputShouldBe("")
  def outputShouldBe(self, expected):
    assert self.result.output.stdoutBuffer == expected
  def outputShouldContainInOrder(self, *expectedPhrases):
    def ascending(numbers):
      return all([x1 < x2 if x1 is not None else True for x1, x2 in 
        zip([None] + numbers, numbers)])
    return ascending([self.result.output.stdoutBuffer.lower().
      index(phrase.lower()) for phrase in expectedPhrases])
  def outputShouldContain(self, *expectedPhrases):
    for phrase in expectedPhrases:
      assert phrase.lower() in self.result.output.stdoutBuffer.lower()
  def outputShouldNotContain(self, *expectedPhrases):
    for phrase in expectedPhrases:
      assert phrase.lower() not in self.result.output.stdoutBuffer.lower()
    
  def setTimeOfDay(self, timeOfDay):
    self.timeOfDay = timeOfDay
  def setClockToTimeAfterInitialTime(self, delta):
    self.time = self.initialTime + delta
  def setClockInitialTime(self, utcTime):
    self.initialTime = self.time = utcTime
    
  def runSibt(self, *arguments):
    output = BufferingOutput()
    executions = ExecutionLogger()
    
    main.run(("--var-dir", str(self.varDir),
      "--config-dir", str(self.configDir)) + arguments,
      output, executions, ConstantClock(self.time, self.timeOfDay))
    
    self.result = RunResult(output, executions)
    
@pytest.fixture
def fixture(tmpdir):
  return SibtSpecFixture(tmpdir)
    
def test_shouldBeAbleToReadAndOutputMultipleBackupRulesFromConfFiles(fixture):
  rule1Src, rule1Dest, rule2Src, rule2Dest = fixture.makeNumberOfTestDirs(4)
  
  fixture.writeRuleFile("rule1", """
  rsync
  
    {0}
  {1}
  every 7w
  """.format(rule1Src, rule1Dest))
  fixture.writeRuleFile("rule2", """
  rdiff
  {0}
  {1}
  15d
  """.format(rule2Src, rule2Dest))
  fixture.writeRuleFile("rule3", """
  rsync
  {0}
  {1}
  """.format(rule1Src, rule1Dest))
  
  fixture.runSibt("--list-config")
  fixture.outputShouldContainInOrder("rule1", "Using rsync", 
    'from "{0}"'.format(rule1Src),
    'to "{0}"'.format(rule1Dest),
    "run every 7 weeks")
  
  fixture.outputShouldContainInOrder("rule2", "Using rdiff", 
    'from "{0}"'.format(rule2Src), 'to "{0}"'.format(rule2Dest),
    "run every 15 days")
  
  fixture.outputShouldContainInOrder("rule3", "run every time")
  fixture.sibtShouldNotExecuteAnyPrograms()
    
def test_shouldIgnoreRuleFilesWithNamesPrefixedWithACapitalN(fixture):
  activeRuleRun = fixture.writeSomeRsyncRule("active-rule")
  
  fixture.writeRuleFile("N-inactive-rule", """
  rdiff-backup
  /one
  /two
  """)
  
  fixture.runSibt("--list-config")
  fixture.outputShouldContain("active-rule", "Using rsync")
  fixture.outputShouldNotContain("inactive-rule", 'from "/one"',
    "rdiff-backup")
  fixture.sibtShouldNotExecuteAnyPrograms()
  
  fixture.runSibt()
  fixture.sibtShouldExecute([activeRuleRun])
  
def test_shouldRunRsyncWithCorrectOptionsAndSourceEndingWithSlash(fixture):
  rule1Src = fixture.newTestDir("folder1")
  rule1Dest = fixture.newTestDir("folder2/")
  rule2Src = fixture.newTestDir("folder3/")
  rule2Dest = fixture.newTestDir("folder3/")
  
  fixture.writeRuleFile("rsync-rule-1", """
  rsync
  {0}
  {1}
  """.format(rule1Src, rule1Dest))
  fixture.writeRuleFile("rsync-rule-2", """
  rsync
  {0}
  {1}
  """.format(rule2Src, rule2Dest))
  
  expectedRule1Src = rule1Src + "/"
  
  fixture.runSibt()
  fixture.outputShouldBeEmpty()
  fixture.sibtShouldExecuteInAnyOrder([
    ("rsync", ("-a", "--partial", "--delete", expectedRule1Src, rule1Dest)),
    ("rsync", ("-a", "--partial", "--delete", rule2Src, rule2Dest))])
  
def test_shouldRunRdiffBackupWithCorrectOptionOnceForEachRdiffRule(fixture):
  rule1Src = fixture.newTestDir("folder")
  rule1Dest = fixture.newTestDir("folder/")
  rule2Src = fixture.newTestDir("source/")
  rule2Dest = fixture.newTestDir("dest")
  
  fixture.writeRuleFile("rdiff-rule1", """
  rdiff
  {0}
  {1}
  """.format(rule1Src, rule1Dest))
  fixture.writeRuleFile("rdiff-rule2", """
  rdiff
  {0}
  {1}""".format(rule2Src, rule2Dest))
  
  fixture.runSibt()
  fixture.sibtShouldExecuteInAnyOrder(
    [("rdiff-backup", ("--remove-older-than", "2W",
    rule1Src, rule1Dest)),
    ("rdiff-backup", ("--remove-older-than", "2W",
    rule2Src, rule2Dest))])
  
def test_ifAFrequencyIsDefinedShouldRunRuleOnlyIfSufficientTimeHasPassed(
  fixture):
  firstRuleRun = fixture.writeSomeRsyncRule("unrestrained-rule")
  secondRuleRun = fixture.writeSomeRsyncRule("every-two-days", "every 2d")
  thirdRuleRun = fixture.writeSomeRsyncRule("every-three-weeks", "every 3w")
  
  def sibtShouldExecuteAtTimeAfterInitialTime(time, programs):
    fixture.setClockToTimeAfterInitialTime(time)
    fixture.runSibt()
    fixture.sibtShouldExecuteInAnyOrder(programs)
  
  fixture.runSibt()
  fixture.sibtShouldExecuteInAnyOrder(
    [firstRuleRun, secondRuleRun, thirdRuleRun])
  
  fixture.runSibt()
  fixture.sibtShouldExecute([firstRuleRun])
  
  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(days=1), [firstRuleRun])
  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(days=2), 
    [firstRuleRun, secondRuleRun])
  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(days=5), 
    [firstRuleRun, secondRuleRun])
  sibtShouldExecuteAtTimeAfterInitialTime(timedelta(weeks=3), 
    [firstRuleRun, secondRuleRun, thirdRuleRun])
  
def test_shouldNotRunAnyRulesDuringConfiguredTimeOfDayToAvoid(fixture):
  ruleRun = fixture.writeSomeRsyncRule("some-rule")
  
  def shouldExecuteAt(timeOfDay, shouldExecute):
    fixture.setTimeOfDay(timeOfDay)
    fixture.runSibt()
    if shouldExecute:
      fixture.sibtShouldExecute([ruleRun])
    else:
      fixture.sibtShouldNotExecuteAnyPrograms()
  
  fixture.writeGlobalConf("""
  avoid time of day from 23:00 to 2:00
  """)
  
  shouldExecuteAt(time(22, 58), True)
  shouldExecuteAt(time(22, 59), True)
  
  shouldExecuteAt(time(23, 0), False)
  shouldExecuteAt(time(23, 5), False)
  shouldExecuteAt(time(0, 5), False)
  shouldExecuteAt(time(1, 0), False)
  shouldExecuteAt(time(2, 0), False)
  
  shouldExecuteAt(time(2, 1), True)
  shouldExecuteAt(time(3, 1), True)
  shouldExecuteAt(time(16, 0), True)
  
  fixture.removeGlobalConf()
  shouldExecuteAt(time(1, 0), True)
  
def test_shouldPrintSyntaxConfErrorsIfTheyExistNDoNothingElseForAnyGivenOptions(
  fixture):
  def expectErrorWithConfFile(title, contents, *errors):
    def checkOutput():
      fixture.sibtShouldNotExecuteAnyPrograms()
      fixture.outputShouldContain("errors", *errors)
    fixture.writeRuleFile(title, contents)
    
    fixture.runSibt()
    checkOutput()
    
    fixture.runSibt("--list-config")
    checkOutput()
    fixture.outputShouldNotContain("rsync")
    
    fixture.removeConfFile(title)
    
  fixture.writeSomeRsyncRule("valid-rule")
  expectErrorWithConfFile("interval-unit", """
  rsync
  /some/place
  /another/one
  every 2y
  """, "invalid interval unit", 'in file "interval-unit"')
  
  expectErrorWithConfFile("interval-format", """
  rsync
  /some/place
  /another/one
  every two days
  """, "parsing interval", 'in file "interval-format"')
  
  expectErrorWithConfFile("global.conf", """
  avoid time of day from 10:00 to
  """, "parsing time of day restriction", 'in file "global.conf"')
  
  expectErrorWithConfFile("too-many-lines", """
  rsync
  /1
  /2
  every 5d
  invalid
  """, "superfluous lines", 'in file "too-many-lines"')
  
def test_shouldOutputGlobalConfInformationWhenListingConfig(fixture):
  fixture.runSibt("--list-config")
  fixture.outputShouldContainInOrder("global.conf", 
    "no time of day restriction")
  
  fixture.writeGlobalConf("avoid time of day from 10:00 to  14:02")
  fixture.runSibt("--list-config")
  fixture.outputShouldContainInOrder("global.conf", 
    "won't run", "from 10:00 to 14:02")
  
def test_shouldSimplyOutputSemanticErrorsButNeverRunAnyRulesIfTheyArePresent(
  fixture):
  def shouldPrintErrorsAndRunNothing(errors, listConfigOutput):
    fixture.runSibt()
    fixture.sibtShouldNotExecuteAnyPrograms()
    fixture.outputShouldContainInOrder(*errors)
    
    fixture.runSibt("--list-config")
    fixture.outputShouldContainInOrder(*errors + listConfigOutput)
  
  srcDir, destDir, srcDir2, destDir2 = fixture.makeNumberOfTestDirs(4)
  
  fixture.writeSomeRsyncRule("valid-rule")
  destinationSubDir = os.path.join(destDir, "some-subdirectory")
  fixture.writeRuleFile("parent-of-dest-exists", """
  rsync
  {0}
  {1}
  """.format(srcDir2, destinationSubDir))
  fixture.runSibt()
  fixture.sibtShouldAmongOthersExecute(rsyncRun(srcDir2 + "/", 
    destinationSubDir))
  
  fixture.writeRuleFile("unknown-tool", """
  supersync3000
  {0}
  {1}""".format(srcDir, destDir))
  
  shouldPrintErrorsAndRunNothing(("errors", "unknown backup program",
    '"supersync3000"'), ("using supersync3000", 'from "{0}"'.format(srcDir)))
  
  fixture.writeRuleFile("source-doesnt-exist", """
  rsync
  /some/source
  {0}""".format(destDir2))
  
  shouldPrintErrorsAndRunNothing(("unknown backup program", 
    "source of", "does not exist", "source-doesnt-exist"), 
    ('from "/some/source"',))
  
  fixture.writeRuleFile("path-exists-but-is-relative", """
  rsync
  {0}
  {1}""".format(srcDir, os.path.relpath(destDir)))
  shouldPrintErrorsAndRunNothing(("destination of",
    "relative"), tuple())
  
def test_shouldOutputInformationAboutIntervalOfRulesWhenListingConfig(fixture):
  def dateStringWithDay(day):
    return "2000-01-{0} 12:00:00.000000 +0000".format(day)
  
  fixture.writeSomeRsyncRule("every-week-rule", "every 1w")
  fixture.writeSomeRsyncRule("unrestricted-rule")
  fixture.setClockInitialTime(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
  
  fixture.runSibt("--list-config")
  fixture.outputShouldContainInOrder("every-week-rule", 
    "last time run: n/a",
    "next time (at the earliest): Due")
  fixture.outputShouldContainInOrder("unrestricted-rule:",
    "next time (at the earliest): Due")
  
  fixture.runSibt()
  fixture.runSibt("--list-config")
  fixture.outputShouldContainInOrder("every-week-rule", 
    "last time run: " + dateStringWithDay("01"),
    "next time (at the earliest): " + dateStringWithDay("08"))
  fixture.outputShouldContainInOrder("unrestricted-rule:",
    "next time (at the earliest): Due")
    
  fixture.setClockToTimeAfterInitialTime(timedelta(days=4))
  fixture.runSibt()
  fixture.runSibt("--list-config")
  fixture.outputShouldContainInOrder("unrestricted-rule:",
    "last time run: " + dateStringWithDay("05"))
  fixture.outputShouldContainInOrder("every-week-rule",
    "next time (at the earliest): " + dateStringWithDay("08"))
  
  fixture.writeGlobalConf("""
    avoid time of day from 11:00 to 14:54
  """)
  fixture.runSibt("--list-config")
  
  fixture.outputShouldContainInOrder("unrestricted-rule",
    "next time (at the earliest): 2000-01-05 14:55:00.000000 +0000")
  fixture.outputShouldContainInOrder("every-week-rule",
    "next time (at the earliest): 2000-01-08 14:55:00.000000 +0000")
  
  
def rsyncRun(src, dest):
  return ("rsync", ("-a", "--partial", "--delete", src, dest))