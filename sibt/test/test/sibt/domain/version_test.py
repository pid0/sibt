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
from datetime import datetime, timezone, timedelta
from sibt.domain.version import Version

def test_shouldThrowExceptionIfItReceivesAnUnawareTime():
  ruleMock = lambda x:x
  ruleMock.name = "name"

  with pytest.raises(Exception):
    Version(ruleMock, datetime(2013, 5, 3, 20, 10, 3))

  Version(ruleMock, datetime(2014, 2, 10, tzinfo=timezone(timedelta(hours=5))))

def test_shouldBeAbleToShowItselfAsCommaSeparatedStringWithUTCTime():
  ruleMock = lambda x:x
  ruleMock.name = "some-rule"
  assert Version(ruleMock, datetime(2015, 3, 6, 18, 15, 30, 
      tzinfo=timezone(timedelta(hours=2)))).strWithUTCW3C == \
      "some-rule,2015-03-06T16:15:30"

