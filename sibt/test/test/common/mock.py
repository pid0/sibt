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

  def matches(self, args):
    return self.matcher(args)

  def __repr__(self):
    return "CallMatcher{0}".format((self.funcName, self.matcher, 
        self.params))

class ExactCall(object):
  def __init__(self, funcName, args, params):
    self.funcName = funcName
    self.expectedArgs = args
    self.params = params

  def matches(self, args):
    return args == self.expectedArgs

  def __repr__(self):
    return "ExactCall{0}".format((self.funcName, self.expectedArgs, 
        self.params))

def call(funcName, args, **kwargs):
  return ExactCall(funcName, args, 
      CallParams.construct(**kwargs))
def callMatching(funcName, matcher, **kwargs):
  return CallMatcher(funcName, lambda args: matcher(*args), 
      CallParams.construct(**kwargs))
def callMatchingTuple(funcName, matcher, **kwargs):
  return CallMatcher(funcName, matcher, CallParams.construct(**kwargs))

def mock():
  return Mock()

class Mock(object):
  def __init__(self):
    self.__expectedCalls = []
    self.inOrder = True

  def clearExpectedCalls(self):
    self.__expectedCalls = []

  def expectCallsInAnyOrder(self, *expectedCalls):
    self.__expectedCalls += list(expectedCalls)
    self.inOrder = False
  def expectCallsInOrder(self, *expectedCalls):
    self.__expectedCalls += list(expectedCalls)
    self.inOrder = True

  def checkExpectedCalls(self):
    expectedCalls = self.__expectedCalls
    remainingCalls = [call for call in expectedCalls if 
        not call.params.anyNumber]
    descriptions = [repr(call) for call in remainingCalls]
    assert len(remainingCalls) == 0, "{0} expected calls remain: {1}".format(
        len(remainingCalls), descriptions)

  def __getattr__(self, name):
    def callHandler(*args):
      message = "{0} unexpectedly called with args {1}".format(name, args)
      expectedCalls = self.__expectedCalls
      mandatoryCalls = [call for call in expectedCalls if
          not call.params.anyNumber]
      matchingCalls = [call for call in expectedCalls if
          call.funcName == name and call.matches(args)]
      assert len(matchingCalls) > 0, message
      nextCall = matchingCalls[0]
      
      if self.inOrder:
        assert len(mandatoryCalls) == 0 or \
            nextCall == mandatoryCalls[0] or \
            nextCall.params.anyNumber

      if not nextCall.params.anyNumber:
        self.__expectedCalls.remove(nextCall)
      return nextCall.params.returnValue

    return callHandler

