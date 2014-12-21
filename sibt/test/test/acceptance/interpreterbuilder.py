from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local

class InterpreterBuilder(ConfigObjectBuilder):
  def __init__(self, paths, sysPaths, foldersWriter, name, 
      execChecker, kwParams):
    super().__init__(paths, sysPaths, foldersWriter, name, kwParams)
    self.execChecker = execChecker

  def withBashCode(self, code):
    return self.withContent("#!/usr/bin/env bash\n" + code)
  def withCode(self, code):
    return self.withContent(code)
  def withTestOptionsCode(self):
    return self.withBashCode("""echo KeepCopies
      echo AddFlags""")

  def expecting(self, *execExpectations):
    return self._withParams(expectations=self.expectations + 
        list(execExpectations))
  def allowing(self, *expectations):
    return self.expecting(*(expectation + ({"anyNumber": True},) for 
        expectation in expectations))

  def _allowingWritesToCalls(self):
    return self.allowing((lambda args: args[0] == "writes-to", ""))
  def allowingSetupCallsExceptOptions(self):
    return self._allowingWritesToCalls()
  def allowingSetupCalls(self):
    return self.allowingSetupCallsExceptOptions().allowing((
        lambda args: args[0] == "available-options", ""))

  def withTestOptions(self):
    return self.expecting((lambda args: args[0] == "available-options", 
      "AddFlags\nKeepCopies\n"))

  def reMakeExpectations(self):
    self.execChecker.expectCalls(*[(str(self.path),) + expectation for 
      expectation in self.expectations])
    return self

  def write(self, toReadonlyDir=False):
    path = local(self.configuredPaths.readonlyInterpretersDir).join(
        self.name) if toReadonlyDir else self.path

    path.write(self.kwParams.get(
      "content", "#!/usr/bin/env bash\necho foo"))
    path.chmod(0o700)
    self.reMakeExpectations()
    return self

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return InterpreterBuilder(paths, sysPaths, foldersWriter, name,
        self.execChecker, kwParams)

  @property
  def expectations(self):
    return self.kwParams.get("expectations", [])
  @property
  def path(self):
    return local(self.configuredPaths.interpretersDir).join(self.name)
