import argparse
import sys

class CmdLineArgs(object):
  def __init__(self, action, options):
    self.action = action
    self.options = options

class CmdLineArgsParser(object):
  def parseArgs(self, args):
    if len(args) == 0:
      args = ["list"]

    parser = argparse.ArgumentParser(description="Simple Backup Tool")
    parser.add_argument("--config-dir")
    parser.add_argument("--var-dir")
    parser.add_argument("--readonly-dir")
    parser.add_argument("--no-sys-config", action="store_true")
    parser.add_argument("--utc", action="store_true")
    subs = parser.add_subparsers(title="actions", dest="action", 
      metavar="list|sync")

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
    
    parsedArgs = vars(parser.parse_args(args))
    cmdLineArgs = dict((key.replace("_", '-'), value) for 
        (key, value) in parsedArgs.items() if value is not None)
    
    ret = CmdLineArgs(parsedArgs["action"], cmdLineArgs)

    return ret
