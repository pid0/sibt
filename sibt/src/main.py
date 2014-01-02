from sibt.parallelprocessrunner import ParallelProcessRunner
from sibt.stdoutput import StdOutput
import sys
from sibt.configuration.configdirreader import ConfigDirReader
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

def run(cmdLineArgs, output, processRunner, clock):
  argParser = CmdLineArgsParser()
  args = argParser.parseArgs(cmdLineArgs)
  
  try:
    configuration, configErrors = readConfig(args.configDir, output)
  except ConfigParseException as ex:
    output.println("Configuration parsing errors:")
    output.println(ex)
    return
  
  executionTimeRepo = ExecutionTimeFileRepo(args.varDir)
  rulesFilter = IntervalBasedRulesFilter(executionTimeRepo, clock)
  
  rulesRunner = RuleSetRunner(processRunner, rulesFilter, externalProgramConfs)
  
  if args.listConfig:
    ConfigPrinter().printConfig(configuration, output, rulesFilter)
    return

  if len(configErrors) == 0:
    executeRulesWithConfig(configuration, rulesRunner, rulesFilter, 
      executionTimeRepo, clock)
  
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
    run(sys.argv[1:], StdOutput(), ParallelProcessRunner(), 
      UTCCurrentTimeClock())