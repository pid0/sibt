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

import unicodedata
from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode

def isCombining(c):
  return unicodedata.combining(c) != 0

class DisplayString(CaseClassEqualityHashCode):
  def __init__(self, string):
    self.string = string
    self.length = 0
    self._updateLength(string)
  
  def _append(self, string):
    self.string = self.string + string
    self._updateLength(string)
  
  def _walkString(self, string, func):
    displayWidth = 0
    for codepointWidth, c in enumerate(string):
      if isCombining(c):
        continue
      if unicodedata.east_asian_width(c) in ["F", "W"]:
        displayWidth += 2
      else:
        displayWidth += 1

      ret = func(c, displayWidth, codepointWidth)
      if ret is not None:
        return ret

  def partition(self, displayIndex):
    if displayIndex >= self.length:
      return self, DisplayString("")

    leftPart = DisplayString("")
    leftLength = 0
    def returnIfLongEnough(c, displayWidth, codepointWidth):
      if displayWidth > displayIndex:
        return leftPart, DisplayString(self.string[codepointWidth:])
      leftPart._append(c)

    return self._walkString(self.string, returnIfLongEnough)

  def index(self, needle):
    lastWidth = [0]
    def returnWhenFound(_, displayWidth, i):
      if self.string.startswith(needle, i):
        return lastWidth[0]
      lastWidth[0] = displayWidth

    ret = self._walkString(self.string, returnWhenFound)
    if ret is None:
      raise ValueError()
    return ret

  def __getitem__(self, key):
    return DisplayString(self.string[key])

  def _updateLength(self, newString):
    def returnWhenAllConsumed(_, length, index):
      if index == len(newString) - 1:
        return length
    self.length += self._walkString(newString, returnWhenAllConsumed) or 0
  
  def __len__(self):
    return self.length

  @property
  def codepointLen(self):
    return len(self.string)
  
  def __str__(self):
    return self.string
  def __repr__(self):
    return "DisplayString({0})".format(repr(self.string))
