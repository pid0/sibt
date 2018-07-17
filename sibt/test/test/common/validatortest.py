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
from test.common.builders import ruleSet, mockRule, mockSched
from test.common import mock

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.dirCounter = 0
    self.nameCounter = 0

  def validLocDir(self):
    self.dirCounter = self.dirCounter + 1
    ret = self.tmpdir.mkdir("dir" + str(self.dirCounter))
    ret.join("file").write("")
    return ret

  def mockRule(self, loc1, loc2, name=None, **kwargs):
    sched = mockSched()
    sched.check = lambda *args: []
    self.nameCounter += 1
    return mockRule(loc1=loc1, loc2=loc2, 
        name=name or "rule-" + str(self.nameCounter),
        scheduler=sched, **kwargs)

  def validRule(self):
    return self.mockRule(self.validLocDir(), self.validLocDir())

def schedCallWithRules(action, *rules, **kwargs):
  return mock.callMatching(action, lambda schedulingSet:
      set(schedulingSet) == set(rule.scheduling for rule in rules),
      **kwargs)

@pytest.fixture
def fix(tmpdir):
  return Fixture(tmpdir)

class ValidatorTest(object):
  def test_validatorShouldReturnNoErrorsIfTheRulesAreOk(self, fix):
    validator = self.construct()
    assert validator.validate(ruleSet(fix.validRule(), fix.validRule())) == []
