import argparse
import sys

class Option(object):
  def __init__(self, name, boolean=False):
    self.name = name
    self.boolean = boolean
    self.cmdLineWord = "--" + name

  def addToParser(self, parser):
    action = "store_true" if self.boolean else "store"
    parser.add_argument(self.cmdLineWord, action=action)

  def cmdLineWordsFromParsedArgs(self, options):
    if self.name not in options or \
      (self.boolean and options[self.name] == False):
      return []
    if self.boolean:
      return [self.cmdLineWord]
    return [self.cmdLineWord, options[self.name]]

def opt(*args):
  return Option(*args)

GlobalOpts = [opt("config-dir"), 
  opt("var-dir"), 
  opt("readonly-dir"), 
  opt("no-sys-config", True),
  opt("no-checks", True),
  opt("utc", True)]

class CmdLineArgs(object):
  def __init__(self, action, options):
    self.action = action
    self.options = options
    self.globalOptionsArgs = []

    for globalOpt in GlobalOpts:
      self.globalOptionsArgs += globalOpt.cmdLineWordsFromParsedArgs(
          self.options)

class CmdLineArgsParser(object):
  def parseArgs(self, args):
    parser = argparse.ArgumentParser(description="Simple Backup Tool")
    for option in GlobalOpts:
      option.addToParser(parser)

    subs = parser.add_subparsers(title="actions", dest="action", 
      metavar="list|sync|versions-of|restore|list-files")

    listAction = subs.add_parser("list", aliases=["li"])
    listAction.add_argument("list-type", nargs="?",
        choices=["interpreters", "schedulers", "rules", "all"],
        default="all")

    sync = subs.add_parser("sync")
    sync.add_argument("rule-patterns", nargs="+", action="store")

    syncUncontrolled = subs.add_parser("sync-uncontrolled")
    syncUncontrolled.add_argument("rule-patterns", nargs="+", action="store")

    versionsOf = subs.add_parser("versions-of")
    versionsOf.add_argument("file", action="store")

    def addListFilesLikeArgs(parser):
      parser.add_argument("file", action="store")
      parser.add_argument("version-substrings", action="store", nargs="+")

    restore = subs.add_parser("restore")
    addListFilesLikeArgs(restore)
    restore.add_argument("--to", action="store")

    listFiles = subs.add_parser("list-files")
    addListFilesLikeArgs(listFiles)

    check = subs.add_parser("check")
    check.add_argument("rule-patterns", nargs="+", action="store")

    show = subs.add_parser("show")
    show.add_argument("rule-patterns", nargs="+", action="store")
    
    parsedArgs = vars(parser.parse_args(args))
    cmdLineArgs = dict((key.replace("_", '-'), value) for 
        (key, value) in parsedArgs.items() if value is not None)

    if "action" not in cmdLineArgs:
      cmdLineArgs["action"] = "list"
      cmdLineArgs["list-type"] = "all"
    
    ret = CmdLineArgs(cmdLineArgs["action"], cmdLineArgs)

    return ret
