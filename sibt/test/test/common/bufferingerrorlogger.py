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

from test.common.assertutil import strToTest
import os

class BufferingErrorLogger(object):
  def __init__(self):
    self.clear()

  @property
  def string(self):
    return strToTest(self.stringBuffer)
  
  def log(self, messageFormat, *args):
    self.stringBuffer += messageFormat.format(*args) + os.linesep

  def clear(self):
    self.stringBuffer = ""
