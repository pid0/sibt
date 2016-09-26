from sibt.infrastructure import cliargsparser as cliparser
from sibt.infrastructure.cliargsparser import PosArg, OptArg, SubGroup, \
    SubGroups
import sys

GlobalOpts = [OptArg("config-dir", noOfArgs="1"), 
  OptArg("var-dir", noOfArgs="1"), 
  OptArg("readonly-dir", noOfArgs="1"), 
  OptArg("no-sys-config"),
  OptArg("verbose", "v"),
  OptArg("tty"),
  OptArg("utc")]

class CmdLineArgs(object):
  def __init__(self, parseResult):
    self.action = parseResult.values["command"]
    self.options = parseResult.values
    self.globalOptionsArgs = []

    for globalOpt in GlobalOpts:
      if globalOpt.name in parseResult.options:
        self.globalOptionsArgs += parseResult.options[globalOpt.name].source

class SibtArgsParser(object):
  def __init__(self):
    rulePatterns = PosArg("rule-patterns", noOfArgs="+")
    listFilesLike = [
        PosArg("file"),
        PosArg("version-substrings", noOfArgs="+")]

    self.parser = cliparser.CliParser(GlobalOpts + [
      SubGroups(

      SubGroup(("list", "ls"), 
        SubGroups(
        SubGroup("schedulers"),
        SubGroup("synchronizers"),
        SubGroup("rules", 
          OptArg("full", "f"),
          OptArg("show-sys"),
          PosArg("rule-patterns", noOfArgs="*")),
        SubGroup("all"),
        default="rules")),
      
      SubGroup("schedule", 
        OptArg("dry"),
        rulePatterns),

      SubGroup("sync", 
        PosArg("rule-name"), description=None),

      SubGroup("versions-of",
        PosArg("file")),

      SubGroup("restore", 
        OptArg("to", noOfArgs="1"),
        OptArg("force"),
        *listFilesLike),

      SubGroup("list-files", 
        OptArg("null"),
        OptArg("recursive", "r"),
        *listFilesLike),

      SubGroup("check",
        rulePatterns),

      SubGroup("show", 
        rulePatterns),

      SubGroup("enable",
        PosArg("rule-name"),
        OptArg("as", noOfArgs="1"),
        PosArg("lines", noOfArgs="*")),

      SubGroup("disable", 
        PosArg("rule-name")),

      SubGroup("execute-rule",
        PosArg("rule-name"), description=None),

      default="list")])

  def parseArgs(self, args, stdout, stderr):
    import sys
    exitStatus, result = cliparser.standardParse(self.parser, sys.argv[0], 
        args, stdout, stderr)
    return exitStatus, CmdLineArgs(result) if result is not None else None
