from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from sibt.application import constructRulesValidator
from sibt.infrastructure.synchronousprocessrunner import \
    SynchronousProcessRunner
from sibt.infrastructure.fileobjoutput import FileObjOutput
import os.path
from sibt.application.paths import Paths
from sibt.infrastructure.userbasepaths import UserBasePaths
from sibt.application.eachownlineconfigprinter import EachOwnLineConfigPrinter
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException
from sibt.application.rulesetrunner import RuleSetRunner
from sibt.application.cmdlineargsparser import CmdLineArgsParser
from sibt.application.configrepo import ConfigRepo
import sys
from sibt.infrastructure.pymoduleschedulerloader import PyModuleSchedulerLoader
from sibt.domain import subvalidators

def run(cmdLineArgs, stdout, stderr, processRunner, paths, sysPaths, 
    userId, schedulerLoader):
  argParser = CmdLineArgsParser()
  args = argParser.parseArgs(cmdLineArgs)

  overridePaths(paths, args)
  createNotExistingDirs(paths)

  readSysConf = userId != 0 and not args.options["no-sys-config"]

  try:
    configRepo = ConfigRepo.load(paths, sysPaths, readSysConf, processRunner,
        schedulerLoader, [sys.argv[0]] + args.globalOptionsArgs)
  except (ConfigSyntaxException, ExternalFailureException) as ex:
    printException(ex, stderr)
    return 1

  if args.action in ["sync", "sync-uncontrolled"]:
    matchingRules = configRepo.findSyncRulesByPatterns(
        args.options["rule-patterns"])
    if len(matchingRules) == 0:
      stderr.println("no matching rule {0}".format(
          args.options["rule-patterns"]))
      return 1

  if args.action == "sync":
    validator = subvalidators.AcceptingValidator() if \
        args.options["no-checks"] else constructRulesValidator(
            configRepo.schedulers)
    errors = validator.validate(matchingRules)
    if len(errors) > 0:
      stderr.println("errors in rules:")
      for error in errors:
        stderr.println(error)
      return 1

    for rule in matchingRules:
      rule.schedule()

    for scheduler in configRepo.schedulers:
      scheduler.executeSchedulings()
  elif args.action == "sync-uncontrolled":
    for rule in matchingRules:
      rule.sync()
  elif args.action == "list":
    listConfiguration(EachOwnLineConfigPrinter(stdout), stdout,
        args.options["list-type"], configRepo.rules, configRepo.sysRules, 
        configRepo.interpreters, configRepo.schedulers)
  elif args.action in ["versions-of", "restore", "list-files"]:
    stringsToVersions = dict()
    for rule in configRepo.allRules:
      for version in rule.versionsOf(args.options["file"]):
        string = version.strWithUTCW3C if args.options["utc"] else \
            version.strWithLocalW3C
        stringsToVersions[string] = version

    if args.action == "versions-of":
      if len(stringsToVersions) == 0:
        stderr.println("no backups found")
      for versionString in stringsToVersions.keys():
        stdout.println(versionString)

    if args.action == "restore" or args.action == "list-files":
      matchingVersions = [versionString for versionString in 
          stringsToVersions.keys() if all(substring in versionString for 
              substring in args.options["version-substrings"])]
      if len(matchingVersions) > 1:
        stderr.println("error: version patterns are ambiguous:")
        stderr.println(str(matchingVersions))
        return 1
      if len(matchingVersions) == 0:
        stderr.println("error: no matching version for patterns")
        return 1
      version = stringsToVersions[matchingVersions[0]]

      if args.action == "restore":
        version.rule.restore(args.options["file"], version,
            args.options.get("to", None))
      if args.action == "list-files":
        version.rule.listFiles(args.options["file"], version)


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


def printException(ex, stderr):
  stderr.println(str(ex))
  stderr.println("reason:\n{0}".format(str(ex.__cause__)))

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
    output.println("")
    output.println("interpreters:")
    printer.printInterpreters(interpreters)
    output.println("")
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

def main():
  exitStatus = run(sys.argv[1:], FileObjOutput(sys.stdout), 
      FileObjOutput(sys.stderr),
      SynchronousProcessRunner(), 
      Paths(UserBasePaths.forCurrentUser()),
      Paths(UserBasePaths(0)), os.getuid(), 
      PyModuleSchedulerLoader("schedulers"))
  sys.exit(exitStatus)
