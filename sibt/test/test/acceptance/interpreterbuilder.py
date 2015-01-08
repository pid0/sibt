from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local
from test.common import execmock

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
  def allowing(self, *calls):
    return self._withParams(allowances=self.allowances + list(calls))

  def _allowingWritesToCalls(self):
    return self.allowing(execmock.call(lambda args: args[0] == "writes-to"))
  def allowingSetupCallsExceptOptions(self):
    return self._allowingWritesToCalls()
  def allowingSetupCalls(self):
    return self.allowingSetupCallsExceptOptions().allowing(
        execmock.call(lambda args: args[0] == "available-options"))

  def expectingListFiles(self, matcher):
    return self.expecting(execmock.call(lambda args: args[0] == "list-files" and
      matcher(args), delimiter="\0"))

  def withTestOptions(self):
    return self.expecting(execmock.call(lambda args: args[0] == 
      "available-options", ret=["AddFlags", "KeepCopies"]))

  def reMakeExpectations(self):
    self.execChecker.expect(str(self.path), *self.expectations)
    self.execChecker.allow(str(self.path), *self.allowances)
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
  def allowances(self):
    return self.kwParams.get("allowances", [])
  @property
  def path(self):
    return local(self.configuredPaths.interpretersDir).join(self.name)
