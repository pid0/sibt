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

class PrefixingErrorLogger(object):
  def __init__(self, output, prefix, maximumVerbosity):
    self.output = output
    self.prefix = prefix + ": "
    self.maximumVerbosity = maximumVerbosity

  def _prefixedLines(self, lines):
    return [self.prefix + line for line in lines]
  def _indentedLines(self, lines):
    return [len(self.prefix) * " " + line for line in lines]

  def log(self, messageFormat, *args, verbosity=0, continued=False):
    if verbosity > self.maximumVerbosity:
      return

    message = messageFormat
    if len(args) > 0:
      message = messageFormat.format(*args)

    lines = [line for line in message.split("\n")]
    firstLineFunc = self._indentedLines if continued else self._prefixedLines
    self.output.println("\n".join(firstLineFunc(lines[0:1]) + 
      self._indentedLines(lines[1:])))
