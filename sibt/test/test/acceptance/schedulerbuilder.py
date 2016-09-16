from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local
from test.common import mock
import re

SchedulerFormat = """
availableOptions = {opts}
availableSharedOptions = {sharedOpts}
{initFunc}
{checkFunc}
{runFunc}
{executeFunc}
"""

def emptyFunc(name):
  return "def {0}(*args): pass".format(name)
def failingFunc(name):
  return "def {0}(*args): assert False, 'unexpectedly called'".format(name)
def assertFalse():
  assert False

class SchedulerBuilder(ConfigObjectBuilder):
  def __init__(self, paths, sysPaths, foldersWriter, name, mockRegistry, 
      kwParams):
    super().__init__(paths, sysPaths, foldersWriter, name, kwParams)
    self.mockRegistry = mockRegistry

  def withAllFuncs(self):
    return self._withParams(initFuncCode=emptyFunc("init"),
        checkFuncCode="def check(*args): return []",
        runFuncCode=failingFunc("run"),
        initFunc=lambda *args: None,
        checkFunc=lambda *args: [],
        runFunc=lambda *args: assertFalse())

  def withTestOptions(self):
    return self.withOptions("Interval", "StopAfterFailure")

  def withOptions(self, *newOptions):
    return self._withParams(options=list(newOptions))
  def withSharedOptions(self, *newOptions):
    return self._withParams(sharedOptions=list(newOptions))

  def withInitFuncCode(self, initFuncCode):
    return self._withParams(initFuncCode=initFuncCode)

  def withCheckFunc(self, newCheckFunc):
    return self._withParams(checkFunc=newCheckFunc)

  def withRunFunc(self, newRunFunc):
    return self._withParams(runFunc=newRunFunc)
  def withEmptyRunFuncCode(self):
    return self._withParams(runFuncCode=emptyFunc("run"))
  def withRunFuncCode(self, runFuncCode):
    return self._withParams(runFuncCode=runFuncCode)

  def withExecuteFunc(self, newExecuteFunc):
    return self._withParams(executeFunc=newExecuteFunc)
  def withExecuteFuncCode(self, code):
    return self._withParams(executeFuncCode=code)

  def mock(self):
    mocked = mock.mock()
    mocked.availableOptions = self.options
    mocked.availableSharedOptions = self.sharedOptions
    mocked.name = self.name

    mocked.init = self.kwParams["initFunc"]
    mocked.check = self.kwParams["checkFunc"]
    mocked.run = self.kwParams["runFunc"]
    if "executeFunc" in self.kwParams:
      mocked.execute = self.kwParams["executeFunc"]

    self.path.write("")
    self.reRegister(mocked)
    return mocked, self

  def reRegister(self, mocked):
    self.mockRegistry[self.name] = mocked

  def write(self, toReadonlyDir=False):
    path = local(self.configuredPaths.readonlySchedulersDir).join(self.name) if\
        toReadonlyDir else self.path
    path.write(self.content)
    return self

  def unIndent(self, code):
    lines = [line for line in code.splitlines() if len(line.strip()) > 0]
    spacePrefixLengths = [len(re.match(r"([ ]*)[^ ]", line).group(1)) for 
        line in lines]
    longestCommonPrefix = min(spacePrefixLengths, default=0)
    return "\n".join(line[longestCommonPrefix:] for line in lines)

  @property
  def content(self):
    return SchedulerFormat.format(
        initFunc=self.unIndent(self.kwParams["initFuncCode"]),
        checkFunc=self.unIndent(self.kwParams["checkFuncCode"]),
        runFunc=self.unIndent(self.kwParams["runFuncCode"]),
        executeFunc=self.unIndent(self.kwParams.get("executeFuncCode", "")),
        opts=self.options,
        sharedOpts=self.sharedOptions)
  @property
  def path(self):
    return local(self.configuredPaths.schedulersDir).join(self.name)
  @property
  def options(self):
    return self.kwParams.get("options", [])
  @property
  def sharedOptions(self):
    return self.kwParams.get("sharedOptions", [])

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return SchedulerBuilder(paths, sysPaths, foldersWriter, name, 
        self.mockRegistry, kwParams)

