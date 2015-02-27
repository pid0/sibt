from fnmatch import fnmatchcase
from functools import reduce

class FakeException(Exception):
  def __init__(self, *args):
    super().__init__(*args)

def iterToTest(iterable):
  return TestIterable(iterable)
def strToTest(string):
  return TestString(string)

class TestIterable(object):
  def __init__(self, iterable):
    self.iterable = iterable
    self.andAlso = self

  def shouldContainMatchingInAnyOrder(self, *predicates):
    assert iterableContainsInAnyOrder(self.iterable, *predicates)
    return self
  def shouldContainInAnyOrder(self, *items):
    assert iterableContainsInAnyOrder(self.iterable, *map(equalsPred, items))
    return self
  def shouldContainPropertiesInAnyOrder(self, propertyProducer, *predicates):
    assert iterableContainsPropertiesInAnyOrder(self.iterable, propertyProducer,
        *predicates)
    return self
  def shouldIncludeMatching(self, *predicates):
    for predicate in predicates:
      assert any(predicate(item) for item in self.iterable)
    return self

  def shouldBe(self, expected):
    assert self.iterable == expected
    return self

  def __str__(self):
    return str(self.iterable)
  def __repr__(self):
    return "TestIterable({0})".format(repr(self.iterable))

class TestString(TestIterable):
  def __init__(self, string):
    super().__init__(string)
    self.string = string

  def _matches(self, pattern):
    return fnmatchcase(self.string, pattern)

  def lines(self):
    return [strToTest(line) for line in self.string.splitlines()]

  def shouldBeEmpty(self):
    assert self.string == ""
    return self

  def shouldInclude(self, *items):
    for item in items:
      assert item.lower() in self.string.lower()
    return self
  def shouldNotInclude(self, *items):
    for item in items:
      assert item.lower() not in self.iterable.lower()
    return self
  def shouldIncludeInOrder(self, *phrases):
    string = self.string.lower()
    def includes(phrases, minIndex):
      if len(phrases) == 0:
        return True
      return includes(phrases[1:], 
          string.index(phrases[0].lower(), minIndex) + 1)

    result = includes(phrases, 0)
    assert result, "{0} should be in {1}".format(phrases, self.string)
    return self

  def shouldIncludeLinePatterns(self, *patterns):
    for pattern in patterns:
      assert any(line._matches(pattern) for line in self.lines())
    return self
  def shouldContainLinePatterns(self, *patterns):
    assert len(self.lines()) == len(patterns)
    self.shouldIncludeLinePatterns(*patterns)
    return self

  def __repr__(self):
    return "TestString({0})".format(repr(self.string))

def equalsPred(expectedValue):
  return lambda arg: arg == expectedValue

def iterableContainsInAnyOrder(iterable, *predicates):
  iterableAsList = list(iterable)
  matchers = list(predicates)
  if len(iterableAsList) != len(matchers):
    return False
  
  for x in iterableAsList:
    matchingMatchers = [matcher for matcher in matchers if matcher(x)]
    if len(matchingMatchers) == 0:
      return False
    matchers.remove(matchingMatchers[0])
    
  return True

def iterableContainsPropertiesInAnyOrder(iterable, propertyProducer, 
    *predicates):
  return iterableContainsInAnyOrder(map(propertyProducer, iterable),
      *predicates)

