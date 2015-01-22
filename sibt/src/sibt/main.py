from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from sibt.application.inifilesyntaxruleconfigprinter import \
    IniFileSyntaxRuleConfigPrinter
from sibt.domain import constructRulesValidator
from sibt.infrastructure.coprocessrunner import \
    CoprocessRunner
from sibt.infrastructure.fileobjoutput import FileObjOutput
import os.path
from sibt.application.paths import Paths
from sibt.infrastructure.userbasepaths import UserBasePaths
from sibt.application.eachownlineconfigprinter import EachOwnLineConfigPrinter
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException
from sibt.infrastructure.externalfailureexception import \
    ExternalFailureException
from sibt.infrastructure.interpreterfuncnotimplementedexception import \
    InterpreterFuncNotImplementedException
from sibt.application.cmdlineargsparser import CmdLineArgsParser
from sibt.application.configrepo import ConfigRepo
import sys
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from sibt.domain import subvalidators
from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from sibt.domain.exceptions import ValidationException
from sibt.application.rulesfinder import RulesFinder
from sibt.application.exceptions import RuleNameMismatchException, \
    RulePatternsMismatchException
import functools
from sibt.application.dryscheduler import DryScheduler

def run(cmdLineArgs, stdout, stderr, processRunner, paths, sysPaths, 
    userId, moduleLoader):

  errorLogger = PrefixingErrorLogger(stderr, 0)  
  try:
    argParser = CmdLineArgsParser()
    args = argParser.parseArgs(cmdLineArgs)
    errorLogger = PrefixingErrorLogger(stderr, 
        1 if args.options["verbose"] else 0)

    overridePaths(paths, args)
    createNotExistingDirs(paths)

    readSysConf = userId != 0 and not args.options["no-sys-config"]

    useDrySchedulers = args.options.get("dry", False)

    try:
      configRepo = ConfigRepo.load(paths, sysPaths, readSysConf, processRunner,
          moduleLoader, [sys.argv[0]] + args.globalOptionsArgs,
          functools.partial(wrapScheduler, useDrySchedulers, stdout))
    except (ConfigSyntaxException, ConfigConsistencyException) as ex:
      printKnownException(ex, errorLogger, 
          causeIsEssential=isinstance(ex, ConfigSyntaxException))
      return 1

    rulesFinder = RulesFinder(configRepo)
    validator = subvalidators.AcceptingValidator() if \
        args.options["no-checks"] else constructRulesValidator()

    if args.action in ["schedule", "check"]:
      matchingRuleSet = rulesFinder.findSyncRuleSetByPatterns(
          args.options["rule-patterns"])
    if args.action in ["sync-uncontrolled", "show"]:
      rule = rulesFinder.findRuleByName(args.options["rule-name"],
          args.action == "sync-uncontrolled")

    if args.action == "show":
      showRule(rule, stdout)

    elif args.action == "check":
      errors = validator.validate(matchingRuleSet)
      printValidationErrors(stdout.println, matchingRuleSet, errors, False)
      if len(errors) > 0:
        return 1

    elif args.action == "schedule":
      try:
        matchingRuleSet.schedule(validator)
      except ValidationException as ex:
        printValidationErrors(errorLogger.log, matchingRuleSet, ex.errors, 
            True)
        return 1

    elif args.action == "sync-uncontrolled":
      try:
        rule.sync()
      except Exception as ex:
        errorLogger.log("running rule ‘{0}’ failed ({1})", rule.name,
          str(ex.exitStatus) if isinstance(ex, ExternalFailureException) else
            "<unexpected error>")
        if not isinstance(ex, ExternalFailureException):
          raise
        printKnownException(ex, errorLogger, 1)
        return 1
    elif args.action == "list":
      listConfiguration(EachOwnLineConfigPrinter(stdout), stdout,
          args.options["list-type"], configRepo.userRules.getAll(), 
          configRepo.sysRules.getAll(), configRepo.interpreters, 
          configRepo.schedulers)
    elif args.action in ["versions-of", "restore", "list-files"]:
      stringsToVersions = dict()
      for rule in configRepo.getAllRules():
        for version in rule.versionsOf(args.options["file"]):
          string = version.strWithUTCW3C if args.options["utc"] else \
              version.strWithLocalW3C
          stringsToVersions[string] = version

      if args.action == "versions-of":
        if len(stringsToVersions) == 0:
          errorLogger.log("no backups found")
          return 1
        for versionString in stringsToVersions.keys():
          stdout.println(versionString)

      if args.action == "restore" or args.action == "list-files":
        matchingVersions = [versionString for versionString in 
            stringsToVersions.keys() if all(substring in versionString for 
                substring in args.options["version-substrings"])]
        if len(matchingVersions) > 1:
          errorLogger.log("version patterns are ambiguous: {0}",
              ", ".join(matchingVersions))
          return 1
        if len(matchingVersions) == 0:
          errorLogger.log("no matching version for patterns")
          return 1
        version = stringsToVersions[matchingVersions[0]]

        if args.action == "restore":
          version.rule.restore(args.options["file"], version,
              args.options.get("to", None))
        if args.action == "list-files":
          files = version.rule.listFiles(args.options["file"], version, 
              args.options["recursive"])
          for fileName in files:
            if args.options["null"]:
              stdout.println(fileName, lineSeparator="\0")
            else:
              stdout.println(fileName.replace("\n", r"\n"), lineSeparator="\n")

    return 0
  except (ExternalFailureException, InterpreterFuncNotImplementedException,
      RuleNameMismatchException, RulePatternsMismatchException) as ex:
    printKnownException(ex, errorLogger)
    return 1

def printKnownException(ex, errorLogger, baseVerbosity=0, 
    causeIsEssential=False):
  errorLogger.log(str(ex), verbosity=baseVerbosity)
  errorLogger.log("cause: {0}", str(ex.__cause__), verbosity=baseVerbosity + (
    0 if causeIsEssential else 1))

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

def showRule(rule, output):
  output.println(rule.name + ":")
  IniFileSyntaxRuleConfigPrinter(output).show(rule)

def printValidationErrors(printFunc, ruleSet, errors, printRuleNames):
  if len(errors) > 0 and printRuleNames:
    printFunc("validation of " + ", ".join("‘{0}’".format(rule.name) for \
        rule in ruleSet) + " failed:")
  for error in errors:
    printFunc(error)

def wrapScheduler(useDrySchedulers, stdout, sched):
  return DryScheduler(sched, stdout) if useDrySchedulers else sched

def main():
  exitStatus = run(sys.argv[1:], FileObjOutput(sys.stdout), 
      FileObjOutput(sys.stderr),
      CoprocessRunner(), 
      Paths(UserBasePaths.forCurrentUser()),
      Paths(UserBasePaths(0)), os.getuid(), 
      PyModuleLoader("schedulers"))
  sys.exit(exitStatus)
