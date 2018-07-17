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
from datetime import datetime
from test.integration.synchronizers.synchronizertest import \
    RunnableFileSynchronizerTestFixture 

class Fixture(RunnableFileSynchronizerTestFixture):
  def __init__(self, tmpdir):
    super().__init__(tmpdir)
    self.load("null")

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldOutputTheCurrentDateWhenToldToSync(fixture, capfd):
  fixture.syncer.sync(fixture.optsWith({}))
  stdout, _ = capfd.readouterr()

  assert str(datetime.today().year) in stdout

