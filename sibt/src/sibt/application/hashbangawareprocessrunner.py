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

import os.path

class HashbangAwareProcessRunner(object):
  def __init__(self, runners, wrapped):
    self.wrapped = wrapped
    self.namesToRunners = dict((runner.name, runner) for runner in runners)

  def getOutput(self, program, *args, **kwargs):
    return self.wrapped.getOutput(*self._modifiedArgs(program, args), **kwargs)

  def execute(self, program, *args):
    self.wrapped.execute(*self._modifiedArgs(program, args))

  def _modifiedArgs(self, program, args):
    if os.path.isfile(program):
      with open(program, "r") as programFile:
        firstLine = programFile.readline().strip()
        if firstLine.startswith("#!"):
          hashbangInterpreter = firstLine[2:]
          if hashbangInterpreter in self.namesToRunners:
            return (self.namesToRunners[hashbangInterpreter].path, 
                program) + args
    return (program,) + args
