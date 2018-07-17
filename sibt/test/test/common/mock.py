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

class CallParams(object):
  def __init__(self, returnValue, anyNumber, sideEffectFunc):
    self.returnValue = returnValue
    self.anyNumber = anyNumber
    self.sideEffectFunc = sideEffectFunc

  @classmethod
  def construct(clazz, ret=None, sideEffectFunc=None, anyNumber=False):
    return clazz(ret, anyNumber, sideEffectFunc)

  def __repr__(self):
    return "CallParams{0}".format((self.returnValue, self.anyNumber))

class CallMatcher(object):
  def __init__(self, funcName, matcher, params):
    self.funcName = funcName
    self.matcher = matcher
    self.params = params

  def matches(self, args, kwargs):
    return self.matcher(args, kwargs)

  def __repr__(self):
    return "CallMatcher{0}".format((self.funcName, self.matcher, 
        self.params))

class ExactCall(object):
  def __init__(self, funcName, args, kwargs, params):
    self.funcName = funcName
    self.expectedArgs = args
    self.expectedKwargs = kwargs
    self.params = params

  def matches(self, args, kwargs):
    return args == self.expectedArgs and kwargs == self.expectedKwargs

  def __repr__(self):
    return "ExactCall{0}".format((self.funcName, self.expectedArgs, 
        self.params))

def call(funcName, args, expectedKwargs=dict(), **kwargs):
  return ExactCall(funcName, args, expectedKwargs,
      CallParams.construct(**kwargs))
def callMatching(funcName, matcher, **kwargs):
  return CallMatcher(funcName, lambda args, kwargs: matcher(*args, **kwargs), 
      CallParams.construct(**kwargs))
def callMatchingTuple(funcName, matcher, **kwargs):
  return CallMatcher(funcName, lambda args, kwargs: matcher(args), 
      CallParams.construct(**kwargs))

AnyArgs = lambda *args, **kwargs: True

def mock(name="mock object"):
  return Mock(name)

class ExpectationGroup(object):
  def __init__(self, expectedCalls, inOrder):
    self.expectedCalls = expectedCalls
    self.inOrder = inOrder

  def __repr__(self):
    return "ExpectationGroup{0}".format((self.expectedCalls, self.inOrder))


class Mock(object):
  def __init__(self, name):
    self._expectationGroups = []
    self._expectedFuncNames = []
    self.__name = name

  def clearExpectedCalls(self):
    self._expectationGroups = []

  def expectCalls(self, *expectedCalls, inAnyOrder=False):
    anyNumberExpectations, finiteCountExpectations = partitionList(
        lambda call: call.params.anyNumber, expectedCalls)

    self._expectationGroups += [ExpectationGroup(
      list(finiteCountExpectations), not inAnyOrder),
      ExpectationGroup(anyNumberExpectations, False)]
    self._updateExpectedNames()

  def expectCallsInOrder(self, *expectedCalls):
    self.expectCalls(*expectedCalls, inAnyOrder=False)
  def expectCallsInAnyOrder(self, *expectedCalls):
    self.expectCalls(*expectedCalls, inAnyOrder=True)

  def _updateExpectedNames(self):
    self._expectedFuncNames = [call.funcName for group in 
        self._expectationGroups for call in group.expectedCalls]

  def checkExpectedCalls(self):
    remainingCalls = [call for group in self._expectationGroups for call in
        group.expectedCalls if not call.params.anyNumber]
    descriptions = [repr(call) for call in remainingCalls]
    assert len(remainingCalls) == 0, "{0} expected calls remain: {1}".format(
        len(remainingCalls), descriptions)

  def __getattribute__(self, name):
    if name in object.__getattribute__(self, "_expectedFuncNames"):
      raise AttributeError

    return object.__getattribute__(self, name)

  def __getattr__(self, name):
    def callHandler(*args, **kwargs):
      message = "{0} unexpectedly called with args {1}, {2}".format(
          name, args, kwargs)
      callMatching = False
      returnValue = None

      for group in self._expectationGroups:
        expectedCalls = group.expectedCalls
        matchingCalls = [call for call in expectedCalls if
            call.funcName == name and call.matches(args, kwargs)]

        callMatching |= len(matchingCalls) > 0
        if len(matchingCalls) == 0:
          continue

        nextCall = expectedCalls[0] if group.inOrder else\
            matchingCalls[0]
        
        assert matchingCalls[0] == nextCall

        if not nextCall.params.anyNumber:
          group.expectedCalls.remove(nextCall)
        returnValue = nextCall.params.returnValue if returnValue is None else\
            returnValue
        if nextCall.params.sideEffectFunc is not None:
          nextCall.params.sideEffectFunc()

      assert callMatching, message
      return returnValue

    if name not in self._expectedFuncNames:
      raise AttributeError

    return callHandler

  def __repr__(self):
    return "(mock object “{0}”)".format(self.__name)

def partitionList(p, xs):
  return (list(filter(p, xs)), 
      list(filter(lambda *args: not p(*args), xs)))
