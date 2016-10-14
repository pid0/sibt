def locToSSHFSArgs(loc):
  sshURL = "{0}{1}:{2}".format(
      (loc.login + "@") if loc.login != "" else "", loc.host, loc.path)
  return [sshURL] + ([] if loc.port == "" else ["-p", loc.port])
