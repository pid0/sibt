from test.common import mock
from sibt.infrastructure.exceptions import ExternalFailureException

DontCheck = object()

def call(*args, **kwargs):
  return (args, kwargs)

def matcherThrowingNotImplementedFailure(predicate):
  def ret(program, args, delimiter="\n"):
    if predicate(program, args, delimiter):
      raise ExternalFailureException("", (), 200)
    return False
  return ret

def makeMockCall(program, predicateOrTuple, ret=[], delimiter="\n", 
    returningNotImplementedStatus=False, **otherKwargs):
  expectedDelimiter = delimiter
  matcher = (lambda calledProgram, args, delimiter="\n": 
      calledProgram == program and
      (predicateOrTuple(args) if callable(predicateOrTuple) else 
        args == predicateOrTuple) and 
      (delimiter == expectedDelimiter or expectedDelimiter is DontCheck)) 

  return mock.callMatching("getOutput", 
      matcherThrowingNotImplementedFailure(matcher) if \
          returningNotImplementedStatus else matcher, 
          ret=ret, **otherKwargs)

def withAnyNumberIsTrue(kwargs):
  ret = dict(kwargs)
  ret["anyNumber"] = True
  return ret

class ExecMock(object):
  def __init__(self):
    self.reset()

  def reset(self):
    self.mockedExec = mock.mock()
    self.returningNotImplementedStatuses = False

  def expect(self, program, *calls, anyOrder=False):
    self.mockedExec.expectCalls(*[makeMockCall(program, *call[0], **call[1]) 
      for call in calls], inAnyOrder=anyOrder)
  def allow(self, program, *calls):
    self.mockedExec.expectCalls(*[makeMockCall(program, *call[0], 
      **withAnyNumberIsTrue(call[1])) for call in calls], inAnyOrder=True)

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments, delimiter="\n"):
    if self.returningNotImplementedStatuses:
      raise ExternalFailureException("", (), 200)
    return self.mockedExec.getOutput(program, arguments, delimiter=delimiter)

  def check(self):
    self.mockedExec.checkExpectedCalls()
