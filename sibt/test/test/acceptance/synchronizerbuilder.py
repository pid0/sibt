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
from test.common import execmock

class SynchronizerBuilder(ConfigObjectBuilder):
  def __init__(self, paths, sysPaths, foldersWriter, name, 
      execChecker, kwParams):
    super().__init__(paths, sysPaths, foldersWriter, name, kwParams)
    self.execChecker = execChecker

  def withBashCode(self, code):
    return self.withContent("#!/usr/bin/env bash\n" + code)
  def withCode(self, code):
    return self.withContent(code)
  def withTestOptionsCode(self):
    return self.withBashCode("""if [ $1 = available-options ]; then 
      echo KeepCopies
      echo AddFlags; else exit 200; fi""")

  def expecting(self, *execExpectations):
    return self._withParams(expectations=self.expectations + 
        list(execExpectations))
  def allowing(self, *calls):
    return self._withParams(allowances=self.allowances + list(calls))

  def allowingPortSpecialsCalls(self, output=[]):
    return self.allowing(execmock.call(lambda args: 
      args[0] == "info-of-port" and args[1] == "specials", 
      returningNotImplementedStatus=output == [], ret=output))
  def supportingProtocols(self, protocolsLists):
    def allowing(indexString, protocols):
      return ret.allowing(execmock.call(
        lambda args: args == ("info-of-port", indexString), ret=retValue))
    ret = self
    for i in range(len(protocolsLists) + 1):
      retValue = (["0"] + protocolsLists[i]) if i < len(protocolsLists) else []
      ret = allowing(str(i + 1), ret)
    return ret

  def _allowingCheckCall(self):
    return self.allowing(execmock.call(lambda args: 
      args[0] == "check", delimiter="\0", returningNotImplementedStatus=True))
  def _allowingPortCalls(self):
    return self.allowing(execmock.call(lambda args: args[0] == "info-of-port",
      returningNotImplementedStatus=True))
  def _allowingOptionsCalls(self):
    return self.allowing(execmock.call(lambda args: args[0] == 
      "available-options", returningNotImplementedStatus=True))
  def writingToLoc2(self):
    return self.allowing(execmock.call(lambda args: 
      args[0] == "info-of-port" and args[1] == "1", ret=["0", "file", "ssh"])).\
      allowing(execmock.call(lambda args: 
      args[0] == "info-of-port" and args[1] == "2", ret=["1", "file", "ssh"])).\
      allowing(execmock.call(lambda args: 
      args[0] == "info-of-port" and args[1] in ["3", "specials"], ret=[]))
  def allowingSetupCallsExceptOptions(self):
    return self._allowingPortCalls()._allowingCheckCall()
  def allowingSetupCallsExceptPorts(self):
    return self._allowingOptionsCalls()._allowingCheckCall()
  def allowingSetupCalls(self):
    return self._allowingPortCalls().\
        _allowingOptionsCalls().\
        _allowingCheckCall()

  def expectingListFiles(self, matcher=lambda _: True):
    return self.expecting(execmock.call(lambda args: args[0] == "list-files" and
      matcher(args), delimiter="\0"))
  def expectingRestore(self, matcher=lambda _: True):
    return self.expecting(execmock.call(lambda args: args[0] == "restore" and
      matcher(args)))
  def expectingSync(self, matcher=lambda _: True):
    return self.expecting(execmock.call(lambda args: args[0] == "sync" and
      matcher(args)))

  def withOptions(self, *options):
    return self.allowing(execmock.call(lambda args: args[0] == 
      "available-options", ret=list(options)))
  def withTestOptions(self):
    return self.withOptions("AddFlags", "KeepCopies")

  def reMakeExpectations(self):
    self.execChecker.expect(str(self.path), *self.expectations)
    self.execChecker.allow(str(self.path), *self.allowances)
    return self

  def write(self, toReadonlyDir=False):
    path = local(self.configuredPaths.readonlySynchronizersDir).join(
        self.name) if toReadonlyDir else self.path

    path.write(self.kwParams.get(
      "content", "#!/usr/bin/env bash\nexit 200"))
    path.chmod(0o700)
    self.reMakeExpectations()
    return self

  def newBasic(self, paths, sysPaths, foldersWriter, name, kwParams):
    return SynchronizerBuilder(paths, sysPaths, foldersWriter, name,
        self.execChecker, kwParams)

  @property
  def expectations(self):
    return self.kwParams.get("expectations", [])
  @property
  def allowances(self):
    return self.kwParams.get("allowances", [])
  @property
  def path(self):
    return local(self.configuredPaths.synchronizersDir).join(self.name)
