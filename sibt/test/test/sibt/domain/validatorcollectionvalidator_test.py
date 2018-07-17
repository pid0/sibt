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

from sibt.domain.validatorcollectionvalidator import \
    ValidatorCollectionValidator
from test.common import mock

def test_shouldReturnTheErrorsOfTheFirstValidatorGroupThatReturnsSome():
  rules = [object(), object()]
  errors1 = ["first error", "foo"]
  errors2 = ["second error", "bar"]
  errors3 = ["third error", "quux"]
  sub0, sub1, sub2, sub3 = mock.mock(), mock.mock(), mock.mock(), mock.mock()

  sub0.expectCalls(mock.call("validate", (rules,), ret=[]))
  sub1.expectCalls(mock.call("validate", (rules,), ret=errors1))
  sub2.expectCalls(mock.call("validate", (rules,), ret=errors2))
  sub3.expectCalls(mock.call("validate", (rules,), ret=errors3))

  validator = ValidatorCollectionValidator([
    [sub0], 
    [sub2, sub1],
    [sub3]])
  assert set(validator.validate(rules)) == set(errors2 + errors1)

