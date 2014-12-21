from test.common import mock

def tupleToMockCall(expectationTuple):
  kwargs = dict() if len(expectationTuple) == 3 else expectationTuple[3]

  matcher = (lambda args: args[0] == expectationTuple[0] and
      expectationTuple[1](args[1])) if callable(expectationTuple[1]) else (
      lambda args: args[0] == expectationTuple[0] and 
        args[1] == expectationTuple[1])

  return mock.callMatchingTuple("getOutput", matcher, ret=expectationTuple[2], 
      **kwargs)

class ExecMock(object):
  def __init__(self):
    self.mockedExec = mock.mock()
    self.ignoring = False

  def reset(self):
    self.mockedExec.clearExpectedCalls()

  def expectCalls(self, *execs, anyOrder=False):
    self.mockedExec.expectCalls(*map(tupleToMockCall, execs), 
        inAnyOrder=anyOrder)

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments):
    if self.ignoring:
      return ""
    return self.mockedExec.getOutput(program, arguments)

  def check(self):
    self.mockedExec.checkExpectedCalls()
