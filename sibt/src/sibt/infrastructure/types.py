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

class Enum(object):
  class Value(object):
    def __init__(self, name, equatableToNames):
      self.name = name
      self.equatableToNames = equatableToNames

    def __str__(self):
      return self.name

    def __repr__(self):
      return "Enum.Value({0})".format(repr(self.name))

    def __eq__(self, other):
      if self.equatableToNames:
        return self.name == other or self is other
      return self is other

  def __init__(self, *elementNames, equatableToNames=False):
    elements = [Enum.Value(name, equatableToNames) for name in elementNames]
    self.values = elements

    for name, element in zip(elementNames, elements):
      fieldName = name
      if name == "None":
        fieldName += "_"
      setattr(self, fieldName, element)

String = object()
Bool = object()
TimeDelta = object()
File = object()
Positive = object()

Location = object()
