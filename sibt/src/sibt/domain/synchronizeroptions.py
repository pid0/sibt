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

import collections

class SynchronizerOptions(collections.UserDict):
  def __init__(self, options, locOptions):
    self.options = options
    self.locOptions = locOptions
    super().__init__(dict(list(options.items()) + 
      list(zip(self.locKeys, self.locOptions))))

    self.locs = locOptions

  def withNewLocs(self, newLocs):
    return SynchronizerOptions(self.options, newLocs)

  @property
  def locKeys(self):
    return ["Loc" + str(i + 1) for i, _ in enumerate(self.locOptions)]

  @classmethod
  def fromDict(clazz, options):
    normalOpts = dict(options)
    locKeys = [name for name in options.keys() if name.startswith("Loc") and
        all(c.isdigit() for c in name[3:])]
    locKeys.sort(key=lambda locKey: int(locKey[3:]))

    locValues = []
    for locKey in locKeys:
      locValues.append(options[locKey])
      del normalOpts[locKey]
    return clazz(normalOpts, locValues)

  def loc(self, i):
    return self.locs[i - 1]

  def __setitem__(self, key, value):
    super().__setitem__(key, value)
    self.options[key] = value

  def __eq__(self, other):
    if not (hasattr(other, "options") and hasattr(other, "locOptions")):
      return False
    return dict(self) == dict(other)

  def __repr__(self):
    return "SynchronizerOptions{0}".format((self.options, self.locOptions))
