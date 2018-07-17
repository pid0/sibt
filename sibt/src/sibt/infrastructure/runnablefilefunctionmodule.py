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

from sibt.infrastructure.exceptions import ExternalFailureException, \
    ModuleFunctionNotImplementedException

def normalizedLines(lines):
  return [line.strip() for line in lines if line.strip() != ""]

class RunnableFileFunctionModule(object):
  def __init__(self, processRunner, filePath):
    self.processRunner = processRunner
    self.executable = filePath

  def _call(self, execFunction, funcName, positionalArgs, options, **kwargs):
    return self._catchNotImplemented(lambda: execFunction(self.executable, 
      funcName, *(list(positionalArgs) + self._keyValueEncode(options)),
      **kwargs), funcName)

  def callVoid(self, funcName, positionalArgs, options):
    self._call(self.processRunner.execute, funcName, positionalArgs, options)

  def callExact(self, funcName, positionalArgs, options):
    return self._call(self.processRunner.getOutput, funcName, 
        positionalArgs, options, delimiter="\0")

  def callFuzzy(self, funcName, positionalArgs, options):
    return normalizedLines(self._call(self.processRunner.getOutput, funcName, 
      positionalArgs, options, delimiter="\n"))

  def _catchNotImplemented(self, func, funcName):
    try:
      ret = func()
      return ret
    except ExternalFailureException as ex:
      if ex.exitStatus == 200:
        raise ModuleFunctionNotImplementedException(funcName) from ex
      else:
        raise ex

  def _keyValueEncode(self, dictionary):
    return ["{0}={1}".format(key, value) for (key, value) in 
        dictionary.items()]

