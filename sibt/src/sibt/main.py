from sibt.infrastructure.dirtreenormalizer import DirTreeNormalizer
from sibt.application.inifilesyntaxruleconfigprinter import \
    IniFileSyntaxRuleConfigPrinter
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
from sibt.infrastructure.interpreterfuncnotimplementedexception import \
    InterpreterFuncNotImplementedException
from sibt.application.cmdlineargsparser import CmdLineArgsParser
from sibt.application.configrepo import ConfigRepo
import sys
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from sibt.domain import subvalidators
from sibt.application.prefixingerrorlogger import PrefixingErrorLogger

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

    try:
      configRepo = ConfigRepo.load(paths, sysPaths, readSysConf, processRunner,
          moduleLoader, [sys.argv[0]] + args.globalOptionsArgs)
    except (ConfigSyntaxException, ConfigConsistencyException) as ex:
      printKnownException(ex, errorLogger, 
          causeIsEssential=isinstance(ex, ConfigSyntaxException))
      return 1

    if args.action in ["sync", "check"]:
      matchingRules = configRepo.findSyncRulesByPatterns(
          args.options["rule-patterns"])
      if len(matchingRules) == 0:
        errorLogger.log("no rule matching {0}", args.options["rule-patterns"])
        return 1
    if args.action in ["sync-uncontrolled", "show"]:
      rule = configRepo.findSyncRuleByName(args.options["rule-name"])
      if rule is None:
        errorLogger.log("no rule with name ‘{0}’", args.options["rule-name"])
        return 1

    if args.action == "show":
      showRule(rule, stdout)
    elif args.action in ["sync", "check"]:
      validator = subvalidators.AcceptingValidator() if \
          args.options["no-checks"] else constructRulesValidator(
              configRepo.schedulers)
      errors = validator.validate(matchingRules)
      errorPrintFunc = errorLogger.log if args.action == "sync" else \
          stdout.println
      if len(errors) > 0:
        errorPrintFunc("errors in rules:")
        for error in errors:
          errorPrintFunc(error)
        return 1

      if args.action == "sync":
        for rule in matchingRules:
          rule.schedule()

        for scheduler in configRepo.schedulers:
          scheduler.executeSchedulings()
    elif args.action == "sync-uncontrolled":
      try:
        rule.sync()
      except Exception as ex:
        errorLogger.log("syncing with rule ‘{0}’ failed ({1})", rule.name,
          str(ex.exitStatus) if isinstance(ex, ExternalFailureException) else
            "<unexpected error>")
        if not isinstance(ex, ExternalFailureException):
          raise
        printKnownException(ex, errorLogger, 1)
        return 1
    elif args.action == "list":
      listConfiguration(EachOwnLineConfigPrinter(stdout), stdout,
          args.options["list-type"], configRepo.userRules, configRepo.sysRules, 
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
          version.rule.listFiles(args.options["file"], version)

    return 0
  except (ExternalFailureException, InterpreterFuncNotImplementedException) \
      as ex:
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

def main():
  exitStatus = run(sys.argv[1:], FileObjOutput(sys.stdout), 
      FileObjOutput(sys.stderr),
      SynchronousProcessRunner(), 
      Paths(UserBasePaths.forCurrentUser()),
      Paths(UserBasePaths(0)), os.getuid(), 
      PyModuleLoader("schedulers"))
  sys.exit(exitStatus)
