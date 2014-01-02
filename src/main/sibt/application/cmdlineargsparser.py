import argparse

class CmdLineArgs(object):
  pass

class CmdLineArgsParser(object):
  def parseArgs(self, args):
    parser = argparse.ArgumentParser(description="Simple Backup Tool")
    parser.add_argument("--list-config", action="store_true")
    parser.add_argument("--config-dir", action="store")
    parser.add_argument("--var-dir", action="store")
    
    parsedArgs = vars(parser.parse_args(args))
    cmdLineArgs = dict(item for item in parsedArgs.items() if 
      item[1] is not None)
    
    ret = CmdLineArgs()
    ret.configDir = cmdLineArgs.get("config_dir", "/etc/sibt.d/")
    ret.varDir = cmdLineArgs.get("var_dir", "/var/local/sibt.d")
    ret.listConfig = cmdLineArgs["list_config"]
    return ret