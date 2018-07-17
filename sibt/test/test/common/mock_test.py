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
from test.common import mock

class Fixture(object):
  pass

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldNotHaveAttributesThatArentAssignedOrExpected(fixture):
  mocked = mock.mock()

  assert not hasattr(mocked, "foo")

  with pytest.raises(AttributeError):
    mocked.foo()

def test_shouldAllowExactlyTheExpectedCalls(fixture):
  mocked = mock.mock()
  mocked.expectCalls(mock.callMatching("allowed", 
    lambda a, b: [a, b] == [1, 2]))

  with pytest.raises(AssertionError):
    mocked.allowed(1, 3)

  mocked.allowed(1, 2)
  with pytest.raises(AssertionError):
    mocked.allowed(1, 2)

def test_shouldCheckOrderOfCalls(fixture):
  mocked = mock.mock()
  expectTestCalls(mocked, False)

  with pytest.raises(AssertionError):
    mocked.bar()
  mocked.foo(40)
  mocked.bar()

def test_shouldBeAbleToIgnoreOrder(fixture):
  mocked = mock.mock()
  expectTestCalls(mocked, True)

  mocked.bar()

def test_shouldBeAbleToAllowAnyNumberOfCallsForSomeExpectations(fixture):
  mocked = mock.mock()
  mocked.expectCalls(mock.call("baz", (1,)),
      mock.call("baz", (), anyNumber=True),
      mock.call("foo", (), anyNumber=True), inAnyOrder=False)

  mocked.foo()
  mocked.baz()
  mocked.baz(1)
  mocked.baz()
  mocked.checkExpectedCalls()

def test_shouldBeAbleToSimultaneouslyCheckMultipleGroupsOfExpectations(fixture):
  mocked = mock.mock()
  mocked.expectCalls(mock.call("foo", ()), mock.call("bar", ()))
  mocked.expectCalls(mock.call("bar", ()), mock.call("foo", ()),
      mock.call("quux", ()), inAnyOrder=True)

  mocked.foo()
  mocked.bar()
  with pytest.raises(AssertionError):
    mocked.checkExpectedCalls()
  mocked.quux()
  mocked.checkExpectedCalls()

def test_shouldReturnFirstConfiguredValueThatIsNotNone(fixture):
  mocked = mock.mock()
  mocked.expectCalls(mock.call("foo", ()))
  mocked.expectCalls(mock.call("foo", (), ret=""))
  mocked.expectCalls(mock.call("foo", (), ret=5))

  assert mocked.foo() == ""
  mocked.checkExpectedCalls()

def test_shouldMakeExpectationsOverrideNormalMethods(fixture):
  mocked = mock.mock()
  mocked.foo = lambda arg: None

  mocked.foo(5)

  mocked.expectCalls(mock.call("foo", (2,)))
  with pytest.raises(AssertionError):
    mocked.foo(5)

def test_shouldBeAbleToTestKeywordArguments(fixture):
  mocked = mock.mock()

  mocked.expectCallsInAnyOrder(mock.call("foo", (4,), {"arg": 2}, 
    anyNumber=True),
      mock.callMatching("bar", lambda *args, **kwargs: 
        args == (4,) and kwargs == {"arg": 2}, anyNumber=True))

  mocked.foo(4, arg=2)
  with pytest.raises(AssertionError):
    mocked.foo(4, arg=3)
  with pytest.raises(AssertionError):
    mocked.foo(4)

  mocked.bar(4, arg=2)
  with pytest.raises(AssertionError):
    mocked.bar(4, arg=0)

def expectTestCalls(mockedObject, anyOrder):
  mockedObject.expectCalls(mock.call("foo", (40,)),
      mock.call("bar", ()), inAnyOrder=anyOrder)
