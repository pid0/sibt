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

from sibt.infrastructure.optioninfoparser import OptionInfoParser

def _optInfosFromStrings(strings):
  parser = OptionInfoParser()
  return [parser.parse(optionString) for optionString in strings]

class OptionInfoParsingScheduler(object):
  def __init__(self, protoScheduler):
    self.protoScheduler = protoScheduler

    self._individualOpts = _optInfosFromStrings(
        self.protoScheduler.availableOptions)
    self.availableSharedOptions = _optInfosFromStrings(
        self.protoScheduler.availableSharedOptions)
    self.availableOptions = self._individualOpts + self.availableSharedOptions

  def __getattr__(self, name):
    return getattr(self.protoScheduler, name)
