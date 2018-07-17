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

from sibt.infrastructure.exceptions import \
    SynchronizerFuncNotImplementedException, ExternalFailureException
from sibt.domain.port import Port
from sibt.infrastructure import types
from sibt.domain.optioninfo import OptionInfo

class DefaultValueSynchronizer(object):
  def __init__(self, wrapped):
    self._wrapped = wrapped

  def _getAvailableOptions(self):
    try:
      return self._wrapped.availableOptions
    except SynchronizerFuncNotImplementedException:
      return []

  def _locOptionInfosCorrespondingToPorts(self, ports):
    return [OptionInfo("Loc" + str(i + 1), types.Location) for i in 
        range(len(ports))]

  @property
  def availableOptions(self):
    return self._getAvailableOptions() + \
        self._locOptionInfosCorrespondingToPorts(self.ports)

  def versionsOf(self, *args):
    try:
      return self._wrapped.versionsOf(*args)
    except (SynchronizerFuncNotImplementedException, ExternalFailureException):
      return []

  @property
  def ports(self):
    try:
      return self._wrapped.ports
    except SynchronizerFuncNotImplementedException:
      return [Port(["file"], False), Port(["file"], True)]

  @property
  def onePortMustHaveFileProtocol(self):
    try:
      return self._wrapped.onePortMustHaveFileProtocol
    except SynchronizerFuncNotImplementedException:
      return False

  def check(self, *args):
    try:
      return self._wrapped.check(*args)
    except SynchronizerFuncNotImplementedException:
      return []

  def __getattr__(self, name):
    return getattr(self._wrapped, name)
