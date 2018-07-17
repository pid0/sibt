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
from sibt.application.sibtargsparser import SibtArgsParser
from test.common.assertutil import iterToTest
from test.common.bufferingoutput import BufferingOutput

class Fixture(object):
  def __init__(self):
    self.parser = SibtArgsParser()

  def parseArgs(self, args):
    _, result = self.parser.parseArgs(args, BufferingOutput(), 
        BufferingOutput())
    return result

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldBeAbleToRetainCommandLineWordsThatDetermineGlobalOptions(
    fixture):
  words1 = ["--config-dir", "foo"]
  words2 = ["--utc"]
  args = fixture.parseArgs(words1 + words2 + ["schedule", "*"])

  assert args.globalOptionsArgs == words1 + words2 or \
      args.globalOptionsArgs == words2 + words1

def test_shouldDefaultToListingRules(fixture):
  result = fixture.parseArgs([])
  assert result.action == "list"
  assert result.options["command2"] == "rules"

def test_shouldAllowForListingShortcuts(fixture):
  def assertListAction(result):
    assert result.action == "list"
    assert result.options["command2"] == "rules"

  result = fixture.parseArgs(["ls", "-f"])
  assertListAction(result)
  assert result.options["full"] == True
  assert result.options["rule-patterns"] == []

  result = fixture.parseArgs(["li", "foo", "bar"])
  assertListAction(result)
  assert result.options["full"] == False
  assert result.options["rule-patterns"] == ["foo", "bar"]

def test_shouldNotDefaultToListingIfANonsenseActionIsGiven(fixture):
  assert fixture.parseArgs(["this-action-is-not-defined"]) is None
