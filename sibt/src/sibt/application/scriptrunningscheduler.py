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

from sibt.infrastructure import types
from sibt.domain.optioninfo import OptionInfo

import subprocess

Options = [
    OptionInfo("ExecOnFailure", types.String),
    OptionInfo("ExecBefore", types.String),
    OptionInfo("ExecOnSuccess", types.String)]

class ScriptRunningScheduler(object):
  def __init__(self, wrappedSched):
    self._wrapped = wrappedSched
    self.availableOptions = wrappedSched.availableOptions + Options

  def _executeScript(self, execEnv, scheduling, optionName):
    if optionName in scheduling.options:
      script = scheduling.options[optionName]
      exitCode = execEnv.logSubProcess(script, shell=True,
          environmentVars=dict(SIBT_RULE=scheduling.ruleName))
      if exitCode != 0:
        execEnv.logger.log("{0} failed ({1})", optionName, exitCode)
        return False
    return True

  def execute(self, execEnv, scheduling):
    try:
      succeeded = self._executeScript(execEnv, scheduling, "ExecBefore")

      if succeeded:
        succeeded = self._wrapped.execute(execEnv, scheduling)

      if succeeded:
        succeeded = self._executeScript(execEnv, scheduling, "ExecOnSuccess")
    except:
      self._executeScript(execEnv, scheduling, "ExecOnFailure")
      raise

    if not succeeded:
      self._executeScript(execEnv, scheduling, "ExecOnFailure")
    
    return succeeded

  def check(self, schedulings):
    ret = []
    ret.extend(schedulings.checkOptionsOfEach(self._checkScriptSyntax,
      "ExecOnFailure", "ExecBefore", "ExecOnSuccess"))
    ret.extend(self._wrapped.check(schedulings))
    return ret

  def _checkScriptSyntax(self, optionName, code, ruleName):
    with subprocess.Popen(["bash", "-n", "-c", code + " | cat"], 
        stderr=subprocess.PIPE) as process:
      _, stderrBytes = process.communicate()
      process.wait()
    syntaxErrors = stderrBytes.decode()
    if len(syntaxErrors) > 0:
      return "syntax errors in {0} code of ‘{1}’:\n{2}".format(
        optionName, ruleName, syntaxErrors)

  def __getattr__(self, name):
    return getattr(self._wrapped, name)
