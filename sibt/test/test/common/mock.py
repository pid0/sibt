class CallMatcher(object):
  def __init__(self, funcName, matcher, returnValue):
    self.funcName = funcName
    self.matcher = matcher
    self.returnValue = returnValue

  def matches(self, args):
    return self.matcher(args)

  def __repr__(self):
    return "CallMatcher{0}".format((self.funcName, self.matcher, 
        self.returnValue))

class ExactCall(object):
  def __init__(self, funcName, args, returnValue):
    self.funcName = funcName
    self.expectedArgs = args
    self.returnValue = returnValue

  def matches(self, args):
    return args == self.expectedArgs

  def __repr__(self):
    return "ExactCall{0}".format((self.funcName, self.expectedArgs, 
        self.returnValue))

def call(funcName, args, ret=None):
  return ExactCall(funcName, args, ret)
def callMatching(funcName, matcher, ret=None):
  return CallMatcher(funcName, lambda args: matcher(*args), ret)
def callMatchingTuple(funcName, matcher, ret=None):
  return CallMatcher(funcName, matcher, ret)

def mock():
  return Mock()

class Mock(object):
  def __init__(self):
    self.__expectedCalls = []
    self.inOrder = True

  def expectCallsInAnyOrder(self, *expectedCalls):
    self.__expectedCalls = list(expectedCalls)
    self.inOrder = False
  def expectCallsInOrder(self, *expectedCalls):
    self.__expectedCalls = list(expectedCalls)
    self.inOrder = True

  def checkExpectedCalls(self):
    expectedCalls = self.__expectedCalls
    assert len(expectedCalls) == 0, "{0} expected calls remain".format(
        len(expectedCalls))

  def __getattr__(self, name):
    def callHandler(*args):
      message = "{0} unexpectedly called with args {1}".format(name, args)
      if not self.inOrder:
        matchingCalls = [call for call in self.__expectedCalls if
            call.funcName == name and call.matches(args)]
        assert len(matchingCalls) > 0, message
        nextCall = matchingCalls[0]
      else:
        nextCall = self.__expectedCalls[0]
        assert name == nextCall.funcName, message
        assert nextCall.matches(args), message

      self.__expectedCalls.remove(nextCall)
      return nextCall.returnValue

    return callHandler

