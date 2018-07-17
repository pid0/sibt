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

from sibt.application.locationformatter import locToSSHFSArgs
from test.common.builders import sshLocation

class Test_SSHFSArgsFormatFunctionTest(object):
  def test_shouldPutAColonBetweenHostAndPath(self):
    assert locToSSHFSArgs(sshLocation(host="machine", path="/wiki")) == \
        ["machine:/wiki"]

  def test_shouldPrependLoginNameIfGiven(self):
    assert locToSSHFSArgs(sshLocation(host="host", path="b", login="user")) == \
        ["user@host:b"]

  def test_shouldAddAPortsOptionIfAPortIsGiven(self):
    assert locToSSHFSArgs(sshLocation(host="a", path="b", port="7823")) == \
        ["a:b", "-p", "7823"]
