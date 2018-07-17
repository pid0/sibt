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

class CachingSynchronizer(object):
  def __init__(self, wrapped):
    self._wrapped = wrapped
    self._cachedAttributes = {}

  def _getCachedAttribute(self, name):
    if name not in self._cachedAttributes:
      self._cachedAttributes[name] = getattr(self._wrapped, name)
    return self._cachedAttributes[name]

  def __getattr__(self, name):
    return self._getCachedAttribute(name)
