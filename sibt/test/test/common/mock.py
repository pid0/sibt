class CallParams(object):
  def __init__(self, returnValue, anyNumber):
    self.returnValue = returnValue
    self.anyNumber = anyNumber

  @classmethod
  def construct(clazz, ret=None, anyNumber=False):
    return clazz(ret, anyNumber)

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
    self.inOrder = True
    self.__name = name

  def clearExpectedCalls(self):
    self._expectationGroups = []

  def expectCalls(self, *expectedCalls, inAnyOrder=False):
    anyNumberExpectations, finiteCountExpectations = partitionList(
        lambda call: call.params.anyNumber, expectedCalls)

    self._expectationGroups += [ExpectationGroup(
      list(finiteCountExpectations), not inAnyOrder),
      ExpectationGroup(anyNumberExpectations, False)]

  def expectCallsInOrder(self, *expectedCalls):
    self.expectCalls(*expectedCalls, inAnyOrder=False)
  def expectCallsInAnyOrder(self, *expectedCalls):
    self.expectCalls(*expectedCalls, inAnyOrder=True)

  def checkExpectedCalls(self):
    for group in self._expectationGroups:
      expectedCalls = group.expectedCalls
      remainingCalls = [call for call in expectedCalls if 
          not call.params.anyNumber]

      descriptions = [repr(call) for call in remainingCalls]
      assert len(remainingCalls) == 0, "{0} expected calls remain: {1}".format(
          len(remainingCalls), descriptions)

  def __getattribute__(self, name):
    expectationGroups = object.__getattribute__(self, "_expectationGroups")
    funcNames = [call.funcName for group in expectationGroups
        for call in group.expectedCalls]

    if name in funcNames:
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

      assert callMatching, message
      return returnValue

    return callHandler

  def __repr__(self):
    return "(mock object “{0}”)".format(self.__name)

def partitionList(p, xs):
  return (list(filter(p, xs)), 
      list(filter(lambda *args: not p(*args), xs)))
