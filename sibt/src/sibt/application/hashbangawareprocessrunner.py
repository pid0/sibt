import os.path

class HashbangAwareProcessRunner(object):
  def __init__(self, runners, wrapped):
    self.wrapped = wrapped
    self.namesToRunners = dict((runner.name, runner) for runner in runners)

  def getOutput(self, program, *args):
    return self.wrapped.getOutput(*self._modifiedArgs(program, args))

  def execute(self, program, *args):
    self.wrapped.execute(*self._modifiedArgs(program, args))

  def _modifiedArgs(self, program, args):
    if os.path.isfile(program):
      with open(program, "r") as programFile:
        firstLine = programFile.readline().strip()
        if firstLine.startswith("#!"):
          hashbangInterpreter = firstLine[2:]
          if hashbangInterpreter in self.namesToRunners:
            return (self.namesToRunners[hashbangInterpreter].path, 
                program) + args
    return (program,) + args
