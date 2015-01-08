from test.common import mock

def call(*args, **kwargs):
  return (args, kwargs)


def makeMockCall(program, predicateOrTuple, ret=[], delimiter="\n", 
    **otherKwargs):
  expectedDelimiter = delimiter
  matcher = (lambda calledProgram, args, delimiter="\n": 
      calledProgram == program and
      (predicateOrTuple(args) if callable(predicateOrTuple) else 
        args == predicateOrTuple) and delimiter == expectedDelimiter) 

  return mock.callMatching("getOutput", matcher, ret=ret,
      **otherKwargs)

def withAnyNumberIsTrue(kwargs):
  ret = dict(kwargs)
  ret["anyNumber"] = True
  return ret

class ExecMock(object):
  def __init__(self):
    self.mockedExec = mock.mock()
    self.ignoring = False

  def reset(self):
    self.mockedExec.clearExpectedCalls()

  def expect(self, program, *calls, anyOrder=False):
    self.mockedExec.expectCalls(*[makeMockCall(program, *call[0], **call[1]) 
      for call in calls], inAnyOrder=anyOrder)
  def allow(self, program, *calls):
    self.mockedExec.expectCalls(*[makeMockCall(program, *call[0], 
      **withAnyNumberIsTrue(call[1])) for call in calls], inAnyOrder=True)

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments, delimiter="\n"):
    if self.ignoring:
      return []
    return self.mockedExec.getOutput(program, arguments, delimiter=delimiter)

  def check(self, callsMustHaveFinished=False):
    self.mockedExec.checkExpectedCalls()
