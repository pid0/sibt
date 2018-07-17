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

class LineBufferedLogger(object):
  def __init__(self):
    self.__buffer = b""

  def write(self, chunk, **kwargs):
    lines = chunk.split(b"\n")
    for i, line in enumerate(lines[:-1]):
      fullLine = line + b"\n"
      if i == 0:
        fullLine = self.__buffer + fullLine
      self.writeLine(fullLine, **kwargs)

    if len(lines) > 1:
      self.__buffer = b""
    self.__buffer += lines[-1]

  def close(self):
    if len(self.__buffer) > 0:
      self.writeLine(self.__buffer)
