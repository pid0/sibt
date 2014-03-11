class ExecMock(object):
  def __init__(self):
    self.execsList = []
    self.ignoring = False

  def expectCalls(self, *execs):
    self.execsList = execs

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments):
    if self.ignoring:
      return ""

    nextExec = self.execsList[0]
    self.execsList = self.execsList[1:]
    assert program == nextExec[0]
    if callable(nextExec[1]):
      assert nextExec[1](arguments)
    else:
      assert arguments == nextExec[1]
    return nextExec[2]

  def check(self):
    assert len(self.execsList) == 0, "expected execs remain"
