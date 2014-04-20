from test.common import mock

class ExecMock(object):
  def __init__(self):
    self.mockedExec = mock.mock()
    self.ignoring = False


  def expectCalls(self, *execs, anyOrder=False):
    expectedCalls = []
    for expectedExec in execs:
      kwargs = dict() if len(expectedExec) == 3 else expectedExec[3]
      if callable(expectedExec[1]):
        call = mock.callMatchingTuple("getOutput", (lambda expected:
            lambda args: args[0] == expected[0] and 
                expected[1](args[1]))(expectedExec), 
            ret=expectedExec[2], **kwargs) 
      else:
        call = mock.call("getOutput", (expectedExec[0],
            expectedExec[1]), ret=expectedExec[2], **kwargs)

      expectedCalls.append(call)

    if anyOrder:
      self.mockedExec.expectCallsInAnyOrder(*expectedCalls)
    else: 
      self.mockedExec.expectCallsInOrder(*expectedCalls)

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments):
    if self.ignoring:
      return ""
    return self.mockedExec.getOutput(program, arguments)

  def check(self):
    self.mockedExec.checkExpectedCalls()
