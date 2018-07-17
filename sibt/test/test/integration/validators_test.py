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

from test.common.validatortest import fix, ValidatorTest
from test.common.builders import ruleSet
from sibt.domain import constructRulesValidator

class Test_ValidatorCollectionTest(ValidatorTest):
  def construct(self):
    return constructRulesValidator()

  def test_shouldReturnAnErrorIfLoc1EqualsLoc2(self, fix):
    validator = self.construct()

    locDir = fix.validLocDir()
    assert len(validator.validate(ruleSet(
      fix.mockRule(locDir, locDir)))) > 0
