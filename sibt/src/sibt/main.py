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
from sibt.application.tabulatingconfigprinter import TabulatingConfigPrinter
from sibt.application.datetimeformatter import DateTimeFormatter
from sibt.configuration.exceptions import ConfigSyntaxException, \
    ConfigConsistencyException, ConfigurableNotFoundException
from sibt.infrastructure.exceptions import ExternalFailureException, \
    SynchronizerFuncNotImplementedException
from sibt.application.sibtargsparser import SibtArgsParser
from sibt.application.configrepo import ConfigRepo
import sys
from sibt.infrastructure.pymoduleloader import PyModuleLoader
from sibt.domain import subvalidators
from sibt.application.mountpointassertionstruevalidator import \
    MountPointAssertionsTrueValidator
from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from sibt.domain.exceptions import ValidationException, \
    UnsupportedProtocolException, LocationInvalidException, \
    LocationNotAbsoluteException, UnstablePhaseException, LockException, \
    RuleExecutingException
from sibt.application.rulesfinder import RulesFinder
from sibt.application.exceptions import RuleNotFoundException
import functools
from sibt.application.dryscheduler import DryScheduler
from sibt.configuration.optionvaluesparser import parseLocation
from sibt.domain.ruleset import RuleSet
from sibt.infrastructure.unbufferedfile import UnbufferedFile
from sibt.application.loggingscheduler import LoggingScheduler
from sibt.application.defaultimplscheduler import DefaultImplScheduler
from sibt.application.scriptrunningscheduler import ScriptRunningScheduler
from sibt.infrastructure.currenttimeclock import CurrentTimeClock
from sibt.application.executionclosenessdetector import \
    ExecutionClosenessDetector
from sibt.domain.negativeunstablephasedetector import \
    NegativeUnstablePhaseDetector
from sibt.infrastructure.fcntlmutexmanager import FcntlMutexManager
from sibt.application.execenvironment import ExecEnvironment
from sibt.infrastructure.parallelmapper import ParallelMapper
import signal
import os
import getpass
import locale
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
import subprocess
import threading

class FatalSignalException(BaseException):
  def __init__(self, signalNumber, childExitStatus):
    self.signalNumber = signalNumber
    self.childExitStatus = childExitStatus
  
  def __str__(self):
    return "terminating because of " + { signal.SIGINT: "SIGINT", 
        signal.SIGTERM: "SIGTERM" }[self.signalNumber]

signalIgnored = dict()
FatalSignals = [signal.SIGINT, signal.SIGTERM]
receivedSignal = None
def signalHandler(raiseException):
  def handleSignal(signalNumber, _):
    global receivedSignal
    previousSigNumber = receivedSignal
    receivedSignal = signalNumber
    if signalNumber == signal.SIGTERM:
      if previousSigNumber is None:
        os.killpg(os.getpgid(0), signal.SIGTERM)
      else:
        return
    if raiseException:
      raise FatalSignalException(signalNumber, None)
  return handleSignal

def killSelf(signalNumber):
  signal.signal(signalNumber, signal.SIG_DFL)
  os.kill(os.getpid(), signalNumber)

def beforeSubprocessRun():
  if threading.current_thread() != threading.main_thread():
    return

  setFatalSignalsHandler(signalHandler(raiseException=False))

def afterSubprocessRun(exitStatus):
  if threading.current_thread() != threading.main_thread():
    return

  global receivedSignal
  setFatalSignalsHandler(signalHandler(raiseException=True))
  if receivedSignal is not None:
    fatalSignalNo = receivedSignal
    receivedSignal = None
    raise FatalSignalException(fatalSignalNo, exitStatus)

def setFatalSignalsHandler(handler):
  for signalNo in FatalSignals:
    if not signalIgnored[signalNo]:
      signal.signal(signalNo, handler)

def testFatalSignalDispositions():
  for signalNo in FatalSignals:
    signalIgnored[signalNo] = signal.getsignal(signalNo) == signal.SIG_IGN

@contextmanager
def fatalSignalsRetained():
  beforeSubprocessRun()
  try:
    yield
  finally:
    setFatalSignalsHandler(signalHandler(raiseException=True))
  afterSubprocessRun(0)

def logSubProcess(log, subProcessArgs, environmentVars=None, **kwargs):
  if environmentVars is not None:
    os.environ.update(environmentVars)

  with fatalSignalsRetained():
    streamRead, streamWrite = os.pipe()

    with open(streamRead, "rb") as outputReader:
      with subprocess.Popen(subProcessArgs,
          stdout=streamWrite, stderr=streamWrite, **kwargs) as process:
        os.close(streamWrite)
        for chunk in iter(lambda: outputReader.read1(2**10), b""):
          log.write(chunk)

    return process.returncode

def run(cmdLineArgs, stdout, stderr, processRunner, paths, sysPaths, 
    userName, userId, moduleLoader, clock, callToSibtSync):
  locale.setlocale(locale.LC_ALL, "")
  testFatalSignalDispositions()
  setFatalSignalsHandler(signalHandler(raiseException=True))

  errorLogger = PrefixingErrorLogger(stderr, "sibt", 0)  
  try:
    argParser = SibtArgsParser()
    parserExitStatus, args = argParser.parseArgs(cmdLineArgs, stdout, stderr)
    if parserExitStatus is not None:
      return parserExitStatus
    makeErrorLogger = lambda prefix: PrefixingErrorLogger(stderr, prefix,
        1 if args.options["verbose"] else 0)
    errorLogger = makeErrorLogger("sibt")

    overridePaths(paths, args)
    createNotExistingDirs(paths)

    readSysConf = userId != 0 and not args.options["no-sys-config"]

    useDrySchedulers = args.options.get("dry", False)

    currentSibtCall = [sys.argv[0]] + args.globalOptionsArgs
    configRepo = ConfigRepo.load(paths, sysPaths, readSysConf, processRunner,
        clock, moduleLoader, currentSibtCall,
        functools.partial(wrapScheduler, useDrySchedulers, stdout, stderr, 
          clock, args.options["verbose"]),
        makeErrorLogger,
        (lambda rule: True) if args.options.get("show-sys", False) else \
            (lambda rule: rule.options["AllowedForUsers"] == userName))
    validator = constructRulesValidator([MountPointAssertionsTrueValidator()])
    unstablePhaseDetector = ExecutionClosenessDetector(clock,
        timedelta(hours=1))

    if args.action in ["schedule", "check"]:
      matchingRuleSet = RuleSet(configRepo.rulesFinder.findRulesByPatterns(
          args.options["rule-patterns"], onlySyncRules=True))
    if args.action in ["sync", "execute-rule"]:
      rule = configRepo.rulesFinder.getSyncRule(args.options["rule-name"])

    if args.action == "show":
      matchingRules = configRepo.rulesFinder.findRulesByPatterns(
          args.options["rule-patterns"], onlySyncRules=False, 
          keepUnloadedRules=False)
      for i, rule in enumerate(matchingRules):
        if i != 0:
          stdout.println("")
        showRule(rule, stdout)

    elif args.action == "enable":
      return enableRule(stderr, args.options["rule-name"], paths,
          args.options.get("as", ""), args.options["lines"])

    elif args.action == "disable":
      return disableRule(stderr, args.options["rule-name"], paths)

    elif args.action == "check":
      errors = validator.validate(matchingRuleSet)
      printValidationErrors(lambda *_: None, stdout.println, matchingRuleSet, 
          errors)
      if len(errors) > 0:
        return 1

    elif args.action == "schedule":
      try:
        matchingRuleSet.schedule(validator)
      except ValidationException as ex:
        printValidationErrors(errorLogger.log, functools.partial(
          errorLogger.log, continued=True), matchingRuleSet, ex.errors)
        return 1
      except RuleExecutingException as ex:
        printKnownException(ex, errorLogger)
        return 4

    elif args.action == "sync":
      BeforeRunning = object()
      exitStatus = None
      try:
        try:
          rule.sync(validator)
        except ExternalFailureException as ex:
          exitStatus = ex.exitStatus
          printKnownException(ex, errorLogger, 1)
          raise
        except FatalSignalException as ex:
          exitStatus = ex.childExitStatus
          raise
        except ValidationException as ex:
          exitStatus = BeforeRunning
          printValidationErrors(errorLogger.log, functools.partial(
            errorLogger.log, continued=True), [rule], ex.errors)
          raise
      except BaseException as ex:
        errorDesc = str(exitStatus)
        if exitStatus is BeforeRunning:
          errorDesc = "before syncing could start"
        if exitStatus is None:
          errorDesc = "<unexpected error>"
        errorLogger.log("running rule ‘{0}’ failed ({1})", rule.name, errorDesc)

        if isinstance(ex, (ExternalFailureException, ValidationException)):
          return 1
        raise

    elif args.action == "execute-rule":
      execEnv = ExecEnvironment(callToSibtSync(currentSibtCall) + [rule.name],
          None, logSubProcess)
      try:
        succeeded = rule.execute(execEnv, clock, 
            FcntlMutexManager(paths.lockDir))
      except LockException as ex:
        errorLogger.log(
          "‘{0}’ is already executing, could not acquire lock", rule.name, 
          verbosity=1)
        return 4

      if not succeeded:
        return 3

    elif args.action == "list":
      printingToTTY = args.options["tty"] or sys.stdout.isatty()
      printer = TabulatingConfigPrinter(stdout,
          printingToTTY, 0 if not printingToTTY else terminalWidth(),
          DateTimeFormatter(clock, args.options["utc"]))

      keepUnloadedRules = True
      listType = args.options["command2"]
      if args.options["command2"] == "rules" and args.options["full"]:
        listType = "full"
        keepUnloadedRules = False

      if args.options["command2"] == "rules" and \
          len(args.options["rule-patterns"]) > 0:
        rules = configRepo.rulesFinder.findRulesByPatterns(
            args.options["rule-patterns"], onlySyncRules=False, 
            keepUnloadedRules=keepUnloadedRules) 
      elif args.options["command2"] in ["rules", "all"]:
        rules = configRepo.rulesFinder.getAll(keepUnloadedRules=
            keepUnloadedRules)
      else:
        rules = []

      listConfiguration(printer, stdout, listType, rules, 
          configRepo.schedulers, configRepo.synchronizers)

    elif args.action in ["versions-of", "restore", "list-files"]:
      stringsToVersions = dict()
      def getVersions(rule):
        return getVersionsFromRule(errorLogger, clock, rule, 
            locationFromArg(args.options["file"]), 
            args.action != "restore", unstablePhaseDetector)

      mapper = ParallelMapper()
      beforeSubprocessRun()
      versionss = mapper.map(getVersions, configRepo.rulesFinder.getAll())
      afterSubprocessRun(0)

      for versions in versionss:
        for version in versions:
          string = version.strWithUTCW3C if args.options["utc"] else \
              version.strWithLocalW3C
          stringsToVersions[string] = version

      if args.action == "versions-of":
        if len(stringsToVersions) == 0:
          errorLogger.log("no backups found")
          return 1
        sortedVersions = list(stringsToVersions.items())
        sortedVersions.sort(key=lambda item: item[1], reverse=True)
        for versionString, _ in sortedVersions:
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
          errorLogger.log("no matching version")
          return 1
        version = stringsToVersions[matchingVersions[0]]

        if args.action == "restore":
          try:
            detectorForRestoring = NegativeUnstablePhaseDetector() if \
                args.options["force"] else unstablePhaseDetector
            version.rule.restore(locationFromArg(args.options["file"]), version,
                locationFromArg(args.options.get("to", None)), 
                detectorForRestoring)
          except UnstablePhaseException:
            printUnstablePhaseWarning(errorLogger, version.rule.name, 
                "pass --force to restore anyway", isError=True)
            return 1
        if args.action == "list-files":
          def printFile(fileName):
            if args.options["null"]:
              stdout.println(fileName, lineSeparator="\0")
            else:
              stdout.println(fileName.replace("\n", r"\n"), lineSeparator="\n")
          files = version.rule.listFiles(printFile, locationFromArg(
            args.options["file"]), version, args.options["recursive"])

    sys.stdout.flush()
    return 0
  except (FatalSignalException) as ex:
    try:
      cliAction = args.action + ": "
    except (NameError, AttributeError):
      cliAction = ""
    errorLogger.log(cliAction + str(ex))
    killSelf(ex.signalNumber)
  except BrokenPipeError as ex:
    killSelf(signal.SIGPIPE)
  except (ConfigurableNotFoundException) as ex:
    printKnownException(ex, errorLogger, additionalInfo=
        "run ‘$ sibt ls {0}s’ to show possible values".format(ex.unitType))
    return 1
  except (ConfigSyntaxException, ConfigConsistencyException) as ex:
    printKnownException(ex, errorLogger, 
        causeIsEssential=isinstance(ex, ConfigSyntaxException))
    return 1
  except (ExternalFailureException, SynchronizerFuncNotImplementedException,
      RuleNotFoundException, UnsupportedProtocolException, 
      LocationInvalidException) as ex:
    printKnownException(ex, errorLogger)
    return 1

def printKnownException(ex, errorLogger, baseVerbosity=0, 
    causeIsEssential=False, additionalInfo=None):
  errorLogger.log(str(ex), verbosity=baseVerbosity)
  errorLogger.log("cause: {0}", str(ex.__cause__), verbosity=baseVerbosity + (
    0 if causeIsEssential else 1), continued=True)
  if additionalInfo is not None:
    errorLogger.log(additionalInfo, continued=True)

def listConfiguration(printer, output, listType, rules, schedulers, 
    synchronizers):
  if listType == "schedulers":
    printer.printSchedulers(schedulers)
  elif listType == "synchronizers":
    printer.printSynchronizers(synchronizers)
  elif listType == "rules":
    printer.printSimpleRuleListing(rules)
  elif listType == "all":
    output.println("schedulers:")
    printer.printSchedulers(schedulers)
    output.println("")
    output.println("synchronizers:")
    printer.printSynchronizers(synchronizers)
    output.println("")
    output.println("rules:")
    printer.printSimpleRuleListing(rules)
  elif listType == "full":
    printer.printFullRuleListing(rules)

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

def printUnstablePhaseWarning(errorLogger, ruleName, suffix="", 
    isError=False):
  prefix = "error" if isError else "warning"
  if suffix != "":
    suffix = ", " + suffix
  errorLogger.log("{0}: execution of rule ‘{1}’ in less than 1 hour{2}",
      prefix, ruleName, suffix)

def getVersionsFromRule(errorLogger, clock, rule, location,
    printWarnings, unstablePhaseDetector):
  try:
    return rule.versionsOf(location, unstablePhaseDetector)
  except UnstablePhaseException:
    if printWarnings:
      printUnstablePhaseWarning(errorLogger, rule.name)
    return rule.versionsOf(location, NegativeUnstablePhaseDetector())

def showRule(rule, output):
  output.println(rule.name + ":")
  IniFileSyntaxRuleConfigPrinter(output).show(rule)

def printValidationErrors(printFuncForRuleNames, printFunc, ruleSet, errors):
  if len(errors) > 0:
    printFuncForRuleNames("validation of " + ", ".join("‘{0}’".format(
      rule.name) for rule in ruleSet) + " failed:")
  for error in errors:
    printFunc(error)

def wrapScheduler(useDrySchedulers, stdout, stderr, clock, 
    forceLoggingToStderr, sched):
  ret = DryScheduler(sched, stdout) if useDrySchedulers else sched
  ret = DefaultImplScheduler(ret)
  ret = ScriptRunningScheduler(ret)
  return LoggingScheduler(ret, clock, stderr, forceLoggingToStderr)

def enableRule(output, baseName, paths, instanceName, configLines):
  instFilePath = os.path.join(paths.enabledDir, instanceName + "@" + baseName)
  if os.path.isfile(instFilePath):
    output.println("‘{0}’ is already enabled".format(baseName))
    return 1
  with open(instFilePath, "w") as instanceFile:
    instanceFile.write("\n".join(configLines))
  output.println("‘{0}’ written".format(instFilePath))
  return 0

def disableRule(output, ruleName, paths):
  instFilePath = os.path.join(paths.enabledDir, ruleName)
  if not os.path.isfile(instFilePath):
    output.println("‘{0}’ is not an enabled rule".format(ruleName))
    return 1
  os.remove(instFilePath)
  output.println("‘{0}’ removed".format(instFilePath))
  return 0

def locationFromArg(arg):
  if arg is None:
    return None
  try:
    return parseLocation(arg)
  except LocationNotAbsoluteException:
    return parseLocation(os.path.abspath(arg) + 
        ("/" if arg.endswith("/") else ""))

def terminalWidth():
  import shutil
  return shutil.get_terminal_size().columns

def main():
  sys.stderr = UnbufferedFile(sys.stderr.buffer)
  exitStatus = run(sys.argv[1:], FileObjOutput(sys.stdout.buffer), 
      FileObjOutput(sys.stderr),
      CoprocessRunner(beforeSubprocessRun, afterSubprocessRun), 
      Paths(UserBasePaths.forCurrentUser()),
      Paths(UserBasePaths(0)), getpass.getuser(), os.getuid(), 
      PyModuleLoader("schedulers"),
      CurrentTimeClock(),
      lambda currentSibtCall: currentSibtCall + ["sync", "--"])
  sys.exit(exitStatus)
