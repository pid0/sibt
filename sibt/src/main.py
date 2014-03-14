from sibt.infrastructure import collectFilesInDirs
from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.infrastructure.executablefileruleinterpreter import \
    ExecutableFileRuleInterpreter
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from sibt.infrastructure.fileobjoutput import FileObjOutput
from sibt.configuration.dirbasedrulesreader import DirBasedRulesReader
import sys
import os.path
from sibt.application.paths import Paths
from sibt.infrastructure.userbasepaths import UserBasePaths
from sibt.application.eachownlineconfigprinter import EachOwnLineConfigPrinter
from sibt.utccurrenttimeclock import UTCCurrentTimeClock
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException
from sibt.application.rulesetrunner import RuleSetRunner
from sibt.domain.rulefactory import RuleFactory
from sibt.application.cmdlineargsparser import CmdLineArgsParser
from fnmatch import fnmatchcase
from sibt.domain.queuingscheduler import QueuingScheduler

#externalProgramConfs = {
#  "rsync": 
#    FormatStringRulesInterpreter(
#      "rsync -a --partial --delete {src} {dest}",
#      lambda src: src if src.endswith('/') else src + '/'),
#  "rdiff":
#    FormatStringRulesInterpreter(
#      "rdiff-backup --remove-older-than 2W {src} {dest}", lambda x: x)
#  }

def run(cmdLineArgs, stdout, stderr, processRunner, clock, paths, sysPaths, 
    userId, schedulerLoader):
  argParser = CmdLineArgsParser()
  args = argParser.parseArgs(cmdLineArgs)

  overridePaths(paths, args)
  createNotExistingDirs(paths)
  
  interpreters = readInterpreters([paths.interpretersDir, 
    paths.readonlyInterpretersDir] + ([sysPaths.interpretersDir] if 
      userId != 0 else []), processRunner)
  schedulers = readSchedulers([paths.schedulersDir, 
    paths.readonlySchedulersDir] + ([sysPaths.schedulersDir] if 
      userId != 0 else []), schedulerLoader, (sys.argv[0], paths, sysPaths))

  factory = RuleFactory(schedulers, interpreters)
  try:
    rules = readRules(paths.rulesDir, paths.enabledDir, factory)
    sysRules = set() if userId == 0 else readRules(sysPaths.rulesDir, 
        sysPaths.enabledDir, factory)
  except ConfigSyntaxException as ex:
    stderr.println("invalid syntax in file {0}: {1}".format(
        ex.file, ex.message))
    stderr.println("reason:\n{0}".format(ex.__cause__))
    return 1

  if args.action in ["sync", "sync-uncontrolled"]:
    matchingRules = findRulesByPatterns(args.options["rule-patterns"], rules)
    if len(matchingRules) == 0:
      stderr.println("no such rule name")
      return 1

  if args.action == "sync":
    for rule in matchingRules:
      rule.schedule()

    for scheduler in schedulers:
      scheduler.executeSchedulings()
  elif args.action == "sync-uncontrolled":
    for rule in matchingRules:
      rule.sync()
  elif args.action == "list":
    listConfiguration(EachOwnLineConfigPrinter(stdout), stdout,
        args.options["list-type"], rules, sysRules, interpreters, schedulers)

  return 0

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


def listConfiguration(printer, output, listType, rules, sysRules, interpreters, 
    schedulers):
  if listType == "interpreters":
    printer.printInterpreters(interpreters)
  elif listType == "schedulers":
    printer.printSchedulers(schedulers)
  elif listType == "rules":
    printer.printSysRules(sysRules)
    printer.printRules(rules)
  elif listType == "all":
    output.println("schedulers:")
    printer.printSchedulers(schedulers)
    output.println("interpreters:")
    printer.printInterpreters(interpreters)
    output.println("rules:")
    printer.printSysRules(sysRules)
    printer.printRules(rules)

def overridePaths(paths, cmdLineArgs):
  newConfigDir = cmdLineArgs.options.get("config-dir", None)
  newVarDir = cmdLineArgs.options.get("var-dir", None)
  newReadonlyDir = cmdLineArgs.options.get("readonly-dir", None)

  if newConfigDir:
    paths.configDir = newConfigDir
  if newVarDir:
    paths.varDir = newVarDir
  if newReadonlyDir:
    paths.readonlyDir = newReadonlyDir

def createNotExistingDirs(paths):
  DirTreeNormalizer(paths).createNotExistingDirs()

def findRulesByPatterns(patterns, rules):
  enabledRules = [rule for rule in rules if rule.enabled]
  disabledRules = [rule for rule in rules if not rule.enabled]
  ruleLists = [findRulePattern(pattern, enabledRules, 
          disabledRules) for pattern in patterns]
  return [rule for ruleList in ruleLists for rule in ruleList]

def findRulePattern(pattern, enabledRules, disabledRules):
  matchingDisabled = [rule for rule in disabledRules if rule.name == pattern]
  if len(matchingDisabled) == 1:
    return matchingDisabled

  return [rule for rule in enabledRules if fnmatchcase(rule.name, pattern)]

def readRules(rulesDir, enabledDir, factory):
  reader = DirBasedRulesReader(rulesDir, enabledDir, factory)
  return reader.read()

def readInterpreters(dirs, processRunner):
  def load(path, fileName):
    try:
      return ExecutableFileRuleInterpreter.createWithFile(path, fileName, 
        processRunner)
    except ConfigConsistencyException:
      return None

  return collectFilesInDirs(dirs, load)

def readSchedulers(dirs, loader, initArgs):
  return collectFilesInDirs(dirs, lambda path, fileName:
      QueuingScheduler(loader.loadFromFile(path, fileName, initArgs)))

  
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
    exitStatus = run(sys.argv[1:], FileObjOutput(sys.stdout), 
        FileObjOutput(sys.stderr),
        SynchronousProcessRunner(), 
        UTCCurrentTimeClock(), Paths(UserBasePaths.forCurrentUser()),
        Paths(UserBasePaths(0)), os.getuid(), 
        PyModuleSchedulerLoader("schedulers"))
    sys.exit(exitStatus)
