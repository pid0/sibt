from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local
from test.common import mock

SchedulerFormat = """
availableOptions = {opts}
{initFunc}
{checkFunc}
{runFunc}
"""

def emptyFunc(name):
  return "def {0}(*args): pass".format(name)
def failingFunc(name):
  return "def {0}(*args): assert False, 'unexpectedly called'".format(name)

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
        runFunc=lambda *args: None)

  def withTestOptions(self):
    return self.withOptions("Interval", "Syslog")

  def withOptions(self, *newOptions):
    return self._withParams(options=list(newOptions))

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

  def mock(self):
    mocked = mock.mock()
    mocked.availableOptions = self.options
    mocked.name = self.name

    mocked.init = self.kwParams["initFunc"]
    mocked.check = self.kwParams["checkFunc"]
    mocked.run = self.kwParams["runFunc"]

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

  @property
  def content(self):
    return SchedulerFormat.format(
        initFunc=self.kwParams["initFuncCode"],
        checkFunc=self.kwParams["checkFuncCode"],
        runFunc=self.kwParams["runFuncCode"],
        opts=self.options)
  @property
  def path(self):
    return local(self.configuredPaths.schedulersDir).join(self.name)
  @property
  def options(self):
    return self.kwParams.get("options", [])

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return SchedulerBuilder(paths, sysPaths, foldersWriter, name, 
        self.mockRegistry, kwParams)

