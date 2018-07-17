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
from test.common.builders import fakeConfigurable, port, optInfo, \
    mkSyncerOpts, configurableList
from sibt.configuration.rulefromstringoptionsreader import \
    RuleFromStringOptionsReader
from test.common import mock
from sibt.configuration.exceptions import ConfigurableNotFoundException, \
    OptionParseException, ConfigConsistencyException
from test.common.assertutil import strToTest
from sibt.domain import syncrule

class Fixture(object):
  def __init__(self):
    self.ruleFactory = mock.mock()
    self.parser = mock.mock()

  def makeReader(self, scheds, syncers):
     return RuleFromStringOptionsReader(self.ruleFactory, self.parser,
         configurableList(scheds), configurableList(syncers))

@pytest.fixture
def fixture(request):
  ret = Fixture()
  request.addfinalizer(lambda: ret.ruleFactory.checkExpectedCalls())
  request.addfinalizer(lambda: ret.parser.checkExpectedCalls())
  return ret

def test_shouldFindSyncersAndSchedsByTheirNameOptions(fixture):
  sched = fakeConfigurable("sched-b")
  syncer = fakeConfigurable("syncer")

  fixture.parser.parseOptions = lambda _, opts: opts

  fixture.ruleFactory.expectCalls(mock.callMatching("build",
    lambda name, receivedSched, receivedSyncer, *_: name == "sys" and
        receivedSched is sched and receivedSyncer is syncer))

  reader = fixture.makeReader([fakeConfigurable("sched-a"), sched], [syncer])
  reader.readRule("sys", {}, { "Name": "sched-b" }, { "Name": "syncer" }, False)

def test_shouldFailIfSyncersOrSchedsWithNamesOrNameOptionsThemselvesAreNotThere(
    fixture):
  scheduler = fakeConfigurable("the-sched")
  synchronizer = fakeConfigurable("the-syncer")
  reader = fixture.makeReader([scheduler], [synchronizer])

  with pytest.raises(ConfigurableNotFoundException) as ex:
    reader.readRule("rule", {}, {}, { "Name": "synchronizer" }, True)
  assert strToTest(ex.value.message).shouldIncludeInOrder("option", "not")

  with pytest.raises(ConfigurableNotFoundException):
    reader.readRule("name", {}, {"Name": "no"}, {"Name": "the-syncer"}, False)
  with pytest.raises(ConfigurableNotFoundException) as ex:
    reader.readRule("name", {}, {"Name": "the-sched"}, {"Name": "no"}, False)
  assert ex.value.unitName == "no"
  assert ex.value.unitType == "synchronizer"

def test_shouldParseOptionValuesAndRemoveNameBeforePassingThemOn(fixture):
  schedOptInfo, syncerOptInfo = object(), object()
  sched = fakeConfigurable("sched", availableOptions=[schedOptInfo]) 
  syncer = fakeConfigurable("syncer", availableOptions=[syncerOptInfo])
  oldRuleOpts = {"Opt": "abc"}
  oldSchedOpts, oldSyncerOpts = {"Name": "sched", "N": "2"}, \
      {"Name": "syncer", "A": "yes"}
  newSchedOpts, newSyncerOpts = {"N": 2}, {"A": True}

  fixture.parser.expectCallsInAnyOrder(mock.callMatching("parseOptions",
    lambda infos, opts: opts == dict(N="2") and infos[0] is schedOptInfo,
    ret=newSchedOpts), mock.callMatching("parseOptions",
    lambda infos, opts: opts == dict(A="yes") and infos[0] is syncerOptInfo,
    ret=newSyncerOpts), mock.callMatching("parseOptions",
    lambda infos, opts: opts == oldRuleOpts and 
      infos is syncrule.AvailableOptions, ret=oldRuleOpts))

  fixture.ruleFactory.expectCalls(mock.callMatchingTuple("build",
    lambda args: args[3] == oldRuleOpts and args[4] == newSchedOpts and 
    args[5] == mkSyncerOpts(**newSyncerOpts)))

  fixture.makeReader([sched], [syncer]).readRule("name", oldRuleOpts, 
      oldSchedOpts, oldSyncerOpts, True)

def test_shouldWrapAllParseExceptionsItGetsInAConsistencyEx(fixture):
  def fail(_, opts):
    if "A" not in opts or opts["A"] == "3":
      raise OptionParseException(["rule-foo" if "A" not in opts else 
        "sched-bar"])
    return True
  sched, syncer = fakeConfigurable("sched"), fakeConfigurable("syncer")

  fixture.parser.expectCalls(mock.callMatching("parseOptions", fail, 
    anyNumber=True, ret={}))

  with pytest.raises(ConfigConsistencyException) as ex:
    fixture.makeReader([sched], [syncer]).readRule("rule", {},
        {"Name": "sched", "A": "3"}, {"Name": "syncer", "A": "0"}, False)
  strToTest(ex.value.message).shouldIncludeInOrder("[Scheduler]", "sched-bar").\
      andAlso.shouldIncludeInOrder("[Rule]", "rule-foo").andAlso.\
      shouldNotInclude("[Synchronizer]")

