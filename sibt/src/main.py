from sibt.infrastructure import collectFilesInDirs
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from sibt.infrastructure.stdoutput import StdOutput
from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
import sys
from sibt.application.paths import Paths
from sibt.infrastructure.userbasepaths import UserBasePaths
from sibt.configprinter import ConfigPrinter
from sibt.formatstringrulesinterpreter import FormatStringRulesInterpreter
from sibt.utccurrenttimeclock import UTCCurrentTimeClock
from sibt.configuration.configparseexception import ConfigParseException
from sibt.configvalidator import ConfigValidator
from sibt.application.rulesetrunner import RuleSetRunner
from sibt.infrastructure.intervalbasedrulesfilter import \
    IntervalBasedRulesFilter
from sibt.infrastructure.executiontimefilerepo import ExecutionTimeFileRepo
from sibt.application.cmdlineargsparser import CmdLineArgsParser

externalProgramConfs = {
  "rsync": 
    FormatStringRulesInterpreter(
      "rsync -a --partial --delete {src} {dest}",
      lambda src: src if src.endswith('/') else src + '/'),
  "rdiff":
    FormatStringRulesInterpreter(
      "rdiff-backup --remove-older-than 2W {src} {dest}", lambda x: x)
  }

def run(cmdLineArgs, output, processRunner, clock, paths):
  argParser = CmdLineArgsParser()
  args = argParser.parseArgs(cmdLineArgs)
  
  rules = readRules(paths.rulesDir)
  interpreters = readInterpreters(paths.interpretersDir, processRunner)
  schedulers = readSchedulers(paths.schedulersDir)

  if args.action == "sync":
    #TODO error handling
    rule = findName(rules, args.options["rule-name"])
    scheduler = findName(schedulers, rule.schedulerName)
    scheduler.run(rule)
  elif args.action == "sync-uncontrolled":
    rule = findName(rules, args.options["rule-name"])
    interpreter = findName(interpreters, rule.interpreterName)
    interpreter.sync(rule)

  return

  try:
    configuration, configErrors = readConfig(paths.configDir, output)
  except ConfigParseException as ex:
    output.println("Configuration parsing errors:")
    output.println(ex)
    return
  
  executionTimeRepo = ExecutionTimeFileRepo(paths.varDir)
  rulesFilter = IntervalBasedRulesFilter(executionTimeRepo, clock)
  
  rulesRunner = RuleSetRunner(processRunner, rulesFilter, externalProgramConfs)
  
  if args.listConfig:
    ConfigPrinter().printConfig(configuration, output, rulesFilter)
    return

  if len(configErrors) == 0:
    executeRulesWithConfig(configuration, rulesRunner, rulesFilter, 
      executionTimeRepo, clock)

def findName(objects, expectedName):
  matching = [obj for obj in objects if obj.name == expectedName]
#TODO error handling
  return matching[0]

def readRules(directory):
  reader = DirBasedRulesReader(directory)
  return reader.read()

def readInterpreters(directory, processRunner):
  return collectFilesInDirs([directory], lambda path, fileName:
      ExecutableFileRuleInterpreter.createWithFile(path, fileName, 
        processRunner))

def readSchedulers(directory):
  def load(path, fileName):
    try:
      return loader.loadFromFile(path, fileName)
    except(Exception):
      return None

  loader = PyModuleSchedulerLoader("schedulers")
  return collectFilesInDirs([directory], load)

  
def readConfig(configDir, output):
  configReader = ConfigDirReader(configDir)
  
  configuration = configReader.read()
  
  configValidator = ConfigValidator(externalProgramConfs.keys())
  configErrors = configValidator.errorsIn(configuration)
  if len(configErrors) != 0:
    output.println("Semantic configuration errors:")
  for error in configErrors:
    output.println("  " + error)
    
  return (configuration, configErrors)
    
def executeRulesWithConfig(configuration, rulesRunner, rulesFilter, 
  executionTimeRepo, clock):
  if configuration.timeOfDayRestriction != None and \
    clock.localTimeOfDay() in configuration.timeOfDayRestriction:
    return
  
  rulesRunner.runRules(configuration.rules)
    
  for dueRule in rulesFilter.getDueRules(configuration.rules):
    executionTimeRepo.setExecutionTimeFor(dueRule, clock.time())

if __name__ == '__main__':
    run(sys.argv[1:], StdOutput(), SynchronousProcessRunner(), 
      UTCCurrentTimeClock(), Paths(UserBasePaths.forCurrentUser()))
