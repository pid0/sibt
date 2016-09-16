from sibt.infrastructure import types
from sibt.domain.optioninfo import OptionInfo
from sibt.infrastructure.schedulerhelper import checkOptionOfEachScheduling

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
          environmentVars=dict(rule=scheduling.ruleName))
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
    ret.extend(checkOptionOfEachScheduling(schedulings, "ExecOnFailure",
      self._checkScriptSyntax))
    ret.extend(checkOptionOfEachScheduling(schedulings, "ExecBefore",
      self._checkScriptSyntax))
    ret.extend(checkOptionOfEachScheduling(schedulings, "ExecOnSuccess",
      self._checkScriptSyntax))

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
