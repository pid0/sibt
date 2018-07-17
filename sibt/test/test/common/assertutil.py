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

from fnmatch import fnmatchcase
from functools import reduce
import itertools
import re
from sibt.infrastructure.displaystring import DisplayString

class FakeException(Exception):
  def __init__(self, *args):
    super().__init__(*args)

def dictIncludes(dictToTest, expectedItems):
  return all(dictToTest[key] == value for key, value in expectedItems.items())

class AssertionToPredicateProxy(object):
  def __init__(self, constructor):
    self.constructor = constructor

  def __getattr__(self, name):
    def constructPredicate(*args):
      def predicate(objectToTest):
        assertionObject = self.constructor(objectToTest)
        try:
          getattr(assertionObject, name)(*args)
        except AssertionError:
          return False
        return True
      return predicate
    return constructPredicate

def iterToTest(iterable):
  return TestIterable(iterable)
def strToTest(string):
  return TestString(string)
stringThat = AssertionToPredicateProxy(strToTest)

class TestIterable(object):
  def __init__(self, iterable):
    self.list = list(iterable)
    self.iterable = iterable
    self.andAlso = self
    self.but = self

  def shouldContainMatchingInAnyOrder(self, *predicates):
    assert iterableContainsInAnyOrder(self.list, *predicates), \
        repr(self.list)
    return self
  def shouldContainMatching(self, *predicates):
    predicateList = list(predicates)
    assert len(self.list) == len(predicateList)
    for i in range(len(self.list)):
      assert predicateList[i](self.list[i])
    return self
  def shouldContainInAnyOrder(self, *items):
    assert iterableContainsInAnyOrder(self.list, *map(equalsPred, items)), \
        repr(self.list)
    return self
  def shouldContain(self, *items):
    assert len(items) == len(self.list)
    for actualItem, expectedItem in zip(self.list, items):
      assert actualItem == expectedItem
  def shouldContainPropertiesInAnyOrder(self, propertyProducer, *predicates):
    assert iterableContainsPropertiesInAnyOrder(self.list, propertyProducer,
        *predicates), repr(self.list)
    return self
  def shouldIncludeMatching(self, *predicates):
    for predicate in predicates:
      assert any(predicate(item) for item in self.list), repr(self.list)
    return self
  def shouldInclude(self, *items):
    for item in items:
      assert item in self.list

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

  @property
  def ignoringFirstLine(self):
    return strToTest("\n".join(line for line in self.string.splitlines()[1:]))

  def lines(self):
    return [strToTest(line) for line in self.string.splitlines()]

  def shouldBeEmpty(self):
    assert self.string == ""
    return self

  def shouldInclude(self, *items):
    for item in items:
      assert item.lower() in self.string.lower()
    return self
  def shouldIncludeAtLeastOneOf(self, *items):
    assert any(item.lower() in self.string.lower() for item in items)
  def shouldNotInclude(self, *items):
    for item in items:
      assert item.lower() not in self.string.lower()
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
  def shouldContainLinePatternsInOrder(self, *patterns):
    assert len(self.lines()) == len(patterns)
    for line, pattern in zip(self.lines(), patterns):
      assert line._matches(pattern)
    return self

  def shouldBeginInTheSameColumn(self, subString):
    startIndices = set(DisplayString(line.string).index(subString) 
        for line in self.lines())
    assert len(startIndices) == 1
  def shouldHaveLinesNoWiderThan(self, maxLength):
    for line in self.lines():
      assert len(line.string) <= maxLength
  def splitColumns(self):
    def isEmptyAt(string, colIndex):
      return string[colIndex] == " "
    def makeRange(group):
      indices = [element[0] for element in group[1]]
      return (indices[0], indices[-1])
    width = len(self.lines()[0].string)
    colPresenceBits = [0 if all(isEmptyAt(line.string, i) for line in 
      self.lines()) else 1 for i in range(width)]
    columnRanges = [makeRange(group) for group in
        itertools.groupby(enumerate(colPresenceBits), key=lambda x: x[1]) 
        if group[0] == 1]
    return [strToTest("\n".join(line.string[colRange[0]:colRange[1]+1] for 
      line in self.lines())) for colRange in columnRanges]
  def onlyAlphanumeric(self):
    return strToTest("".join(c for c in self.string if c.isalnum() or c == "-"))

  @property
  def ignoringEscapeSequences(self):
    return strToTest(re.sub("\033\\[[0-9]+m", "", self.string))

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

