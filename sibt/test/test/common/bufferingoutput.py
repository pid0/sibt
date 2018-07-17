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

import os
from test.common.assertutil import strToTest

class BufferingOutput(object):
  def __init__(self):
    self.stringBuffer = ""
  
  @property
  def string(self):
    return strToTest(self.stringBuffer)
  
  def println(self, x, lineSeparator=os.linesep):
    self.stringBuffer += str(x) + lineSeparator
