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

from sibt.domain.synchronizeroptions import SynchronizerOptions as SyncerOpts
from collections import OrderedDict

def test_shouldImplementEquals():
  assert SyncerOpts({"A": 2}, ["/tmp"]) == SyncerOpts({"A": 2}, ["/tmp"])
  assert SyncerOpts({"A": 2}, ["/tmp"]) != {"A": 2, "Loc1": "/tmp"}

  opts = SyncerOpts(dict(A=1), [])
  opts["B"] = 2
  opts = opts.withNewLocs(["/mnt"])
  assert opts == SyncerOpts(dict(A=1, B=2), ["/mnt"])

def test_shouldProvideAccessToLocOptionsThroughDictLikeInterface():
  opts = SyncerOpts({"Opt": False}, ["/mnt", "/tmp"])

  assert opts["Loc1"] == "/mnt"
  assert opts["Loc2"] == "/tmp"

  assert dict(opts) == {"Opt": False, "Loc1": "/mnt", "Loc2": "/tmp"}

  assert set([key for key in opts]) == {"Opt", "Loc1", "Loc2"}

def test_shouldHaveFactoryFuncThatTakesADict():
  optDict = OrderedDict()
  optDict["Loc2"] = "/bar"
  optDict["Loc1"] = "/foo"
  assert SyncerOpts.fromDict(optDict) == SyncerOpts({}, ["/foo", "/bar"])
