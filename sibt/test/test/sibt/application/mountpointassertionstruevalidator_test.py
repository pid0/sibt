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

import pytest
from sibt.application.mountpointassertionstruevalidator import \
    MountPointAssertionsTrueValidator
from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockRule, ruleSet
from test.common.assertutil import iterToTest, stringThat
from test.common.fusefs import nonEmptyFSMountedAt, fuseIsAvailable

class Test_MountPointAssertionsTrueValidatorTest(ValidatorTest):
  def construct(self):
    return MountPointAssertionsTrueValidator()
  
  @pytest.mark.skipif(not fuseIsAvailable(), reason="Requires FUSE")
  def test_shouldPrintTheActualMountPointIfTheAssertionTurnsOutFalse(self, fix):
    mountPoint = fix.tmpdir.mkdir("mount")

    with nonEmptyFSMountedAt(mountPoint):
      loc1 = mountPoint.mkdir("sub").mkdir("loc1")
      rule = mockRule(loc1=str(loc1), options=dict(MustBeMountPoint="1"))
      errors = self.construct().validate(ruleSet(rule))

    iterToTest(errors).shouldContainMatching(
        stringThat.shouldInclude("actual", str(mountPoint) + "’"))
