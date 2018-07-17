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

from test.common.builders import fakeConfigurable, port, optInfo, \
    location as loc
from sibt.domain.defaultvaluesynchronizer import DefaultValueSynchronizer
from test.common.assertutil import iterToTest
from sibt.infrastructure import types

def test_shouldAddLocOptInfosToAvailableOptionsBasedOnPorts():
  wrapped = fakeConfigurable("syncer", 
      ports=[port(), port(), port()], availableOptions=[])
  syncer = DefaultValueSynchronizer(wrapped)

  iterToTest(syncer.availableOptions).shouldContainMatching(
      lambda opt: opt.name == "Loc1" and opt.optionType == types.Location,
      lambda opt: opt.name == "Loc2", lambda opt: opt.name == "Loc3")
