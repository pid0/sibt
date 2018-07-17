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

from sibt.infrastructure.linebufferedlogger import LineBufferedLogger

TimeFormat = "%Y-%m-%d %H:%M:%S"

class FileLogger(LineBufferedLogger):
  def __init__(self, filePath, clock, prefix=""):
    super().__init__()
    self.file = open(filePath, "ab")
    self.clock = clock
    self.prefix = prefix
    self.startingNewLine = True

  def writeLine(self, line, **kwargs):
    prefix = "[{0}, {1}] ".format(
        self.clock.now().strftime(TimeFormat), 
        self.prefix)
    self.file.write(prefix.encode())

    self.file.write(line)
    if line[-1:] != b"\n":
      self.file.write(b"\n")
    self.file.flush()

  def close(self):
    super().close()
    self.file.close()
