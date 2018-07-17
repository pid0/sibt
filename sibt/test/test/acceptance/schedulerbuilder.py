# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from test.acceptance.configobjectbuilder import ConfigObjectBuilder
from py.path import local
from test.common import mock
from textwrap import dedent

SchedulerFormat = """
availableOptions = {opts}
availableSharedOptions = {sharedOpts}
{initFunc}
{checkFunc}
{scheduleFunc}
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
        scheduleFuncCode=failingFunc("schedule"),
        initFunc=lambda *args: None,
        checkFunc=lambda *args: [],
        scheduleFunc=lambda *args: assertFalse())

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

  def withScheduleFunc(self, newScheduleFunc):
    return self._withParams(scheduleFunc=newScheduleFunc)
  def withEmptyScheduleFuncCode(self):
    return self._withParams(scheduleFuncCode=emptyFunc("schedule"))
  def withScheduleFuncCode(self, scheduleFuncCode):
    return self._withParams(scheduleFuncCode=scheduleFuncCode)

  def withExecuteFunc(self, newExecuteFunc):
    return self._withParams(executeFunc=newExecuteFunc)
  def withExecuteFuncCode(self, code):
    return self._withParams(executeFuncCode=code)

  def withNextExecutionTimeFunc(self, nextExecutionTime):
    return self._withParams(nextExecutionTimeFunc = nextExecutionTime)

  def mock(self):
    mocked = mock.mock()
    mocked.availableOptions = self.options
    mocked.availableSharedOptions = self.sharedOptions
    mocked.name = self.name

    mocked.init = self.kwParams["initFunc"]
    mocked.check = self.kwParams["checkFunc"]
    mocked.run = self.kwParams["scheduleFunc"]
    if "executeFunc" in self.kwParams:
      mocked.execute = self.kwParams["executeFunc"]
    if "nextExecutionTimeFunc" in self.kwParams:
      mocked.nextExecutionTime = self.kwParams["nextExecutionTimeFunc"]

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
        initFunc=dedent(self.kwParams["initFuncCode"]),
        checkFunc=dedent(self.kwParams["checkFuncCode"]),
        scheduleFunc=dedent(self.kwParams["scheduleFuncCode"]),
        executeFunc=dedent(self.kwParams.get("executeFuncCode", "")),
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

