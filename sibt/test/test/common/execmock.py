from test.common import mock

class ExecMock(object):
  def __init__(self):
    self.mockedExec = mock.mock()
    self.ignoring = False


  def expectMatchingCalls(self, *execs):
    expectedCalls = [mock.callMatchingTuple("getOutput", (lambda expected: 
      lambda args: args[0] == expected[0] and expected[1](args[1]))(
        expectedExec), expectedExec[2]) for expectedExec in execs]
    self.mockedExec.expectCallsInOrder(*expectedCalls)
  def expectCalls(self, *execs):
    expectedCalls = [mock.call("getOutput", (expectedExec[0],
        expectedExec[1]), ret=expectedExec[2]) for expectedExec in execs]
    self.mockedExec.expectCallsInOrder(*expectedCalls)

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments):
    if self.ignoring:
      return ""
    return self.mockedExec.getOutput(program, arguments)

  def check(self):
    self.mockedExec.checkExpectedCalls()
