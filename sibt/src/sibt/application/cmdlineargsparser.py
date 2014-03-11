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
    subs = parser.add_subparsers(title="actions", dest="action", 
      metavar="list|sync")

    listAction = subs.add_parser("list", aliases=["li"])
    listAction.add_argument("list-type", nargs="?",
        choices=["interpreters", "schedulers", "rules", "all"],
        default="all")

    sync = subs.add_parser("sync")
    sync.add_argument("rule-name", action="store")

    syncUncontrolled = subs.add_parser("sync-uncontrolled")
    syncUncontrolled.add_argument("rule-name", action="store")
    
    parsedArgs = vars(parser.parse_args(args))
    cmdLineArgs = dict((key.replace("_", '-'), value) for 
        (key, value) in parsedArgs.items() if value is not None)
    
    ret = CmdLineArgs(parsedArgs["action"], cmdLineArgs)

    return ret
