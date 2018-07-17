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

class SynchronizerFuncNotImplementedException(Exception):
  def __init__(self, synchronizerName, funcName):
    self.synchronizerName = synchronizerName
    self.funcName = funcName

  def __str__(self):
    return "synchronizer ‘{0}’ does not implement ‘{1}’".format(
        self.synchronizerName, self.funcName)

class ExternalFailureException(Exception):
  def __init__(self, program, arguments, exitStatus):
    self.program = program
    self.arguments = arguments
    self.exitStatus = exitStatus

  def __str__(self):
    return "error when calling “{0}” with arguments {1} ({2})".format(
        self.program, self.arguments, self.exitStatus)

class ModuleFunctionNotImplementedException(Exception):
  def __init__(self, funcName):
    self.funcName = funcName

class ParseException(Exception):
  def __init__(self, parsedString, error):
    self.parsedString = parsedString
    self.error = error

  def __str__(self):
    return "error when parsing ‘{0}’: {1}".format(
        repr(self.parsedString), self.error)

