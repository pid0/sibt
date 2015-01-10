from test.common import mock

class OutputIterator(object):
  def __init__(self, lines):
    self.lines = lines
    self.counter = -1

  @property
  def finished(self):
    return self.counter >= len(self.lines)
  def __iter__(self):
    return self
  def __next__(self):
    self.counter += 1
    if self.finished:
      raise StopIteration()
    return self.lines[self.counter]

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
    self.reset()

  def _asIterator(self, output):
    ret = OutputIterator(output)
    self.iterators.append(ret)
    return ret

  def reset(self):
    self.mockedExec = mock.mock()
    self.iterators = []
    self.ignoring = False

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
    return self._asIterator(self.mockedExec.getOutput(
      program, arguments, delimiter=delimiter))

  def check(self, callsMustHaveFinished=False):
    self.mockedExec.checkExpectedCalls()
    if callsMustHaveFinished:
      for iterator in self.iterators:
        assert iterator.finished, "unfinished call with output {0}".format(
            iterator.lines)
