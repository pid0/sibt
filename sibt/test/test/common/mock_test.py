import pytest
from test.common import mock

class Fixture(object):
  pass

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldThrowAppropriateExceptionIfCalledUnexpectedly(fixture):
  mocked = mock.mock()
  with pytest.raises(AssertionError):
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

def expectTestCalls(mockedObject, anyOrder):
  mockedObject.expectCalls(mock.call("foo", (40,)),
      mock.call("bar", ()), inAnyOrder=anyOrder)
