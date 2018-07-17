import subprocess
from sibt.infrastructure.exceptions import ExternalFailureException

ChunkSize = 2048
Nop = lambda *args: None

def decode(bytesObj):
  return bytesObj.decode(errors="surrogateescape")

def spawnProcess(program, arguments, afterForking, **kwargs):
  ret = subprocess.Popen([program] + list(arguments), **kwargs)
  afterForking()
  return ret

def waitAndCheckExitStatus(process, programPath, arguments, afterWaiting):
  process.wait()
  afterWaiting(process.returncode)
  if process.returncode != 0:
    raise ExternalFailureException(programPath, list(arguments), 
        process.returncode)

class CoprocessRunner(object):
  def __init__(self, afterForking=Nop, afterWaiting=Nop):
    self.afterForking = afterForking
    self.afterWaiting = afterWaiting

  def getOutput(self, program, *arguments, delimiter="\n"):
    assert ord(delimiter) < 128
    process = spawnProcess(program, arguments, self.afterForking,
        stdout=subprocess.PIPE)

    return CoprocessRunner.OutputIterator(program, arguments, 
        process, delimiter.encode("utf-8"), self.afterWaiting)

  def execute(self, program, *arguments):
    with spawnProcess(program, arguments, self.afterForking) as process:
      waitAndCheckExitStatus(process, program, arguments, self.afterWaiting)

  class OutputIterator(object):
    def __init__(self, programPath, arguments, process, delimiter, 
        afterWaiting):
      self.programPath = programPath
      self.arguments = arguments
      self.process = process
      self.delimiter = delimiter
      self.stdout = process.stdout
      self.finished = False
      self.returnedFirstLine = False
      self.firstLine = None
      self.buffer = b""
      self.eof = False
      self.afterWaiting = afterWaiting

      self._waitForFirstLine()

    def _waitForFirstLine(self):
      try:
        self.firstLine = self._iterate()
      except StopIteration:
        pass

    def _cleanUp(self):
      def afterWaiting(*args):
        with self.process:
          pass
        self.afterWaiting(*args)
      waitAndCheckExitStatus(self.process, self.programPath, self.arguments,
          afterWaiting)

    def __iter__(self):
      return self

    def _readChunk(self):
      readBytes = self.stdout.read1(ChunkSize)
      self.buffer = self.buffer + readBytes
      if readBytes == b"":
        self.eof = True

    def _iterate(self):
      try:
        if self.finished:
          raise StopIteration()

        while True:
          output = self.buffer
          delimPosition = output.find(self.delimiter)
          if delimPosition != -1:
            self.buffer = output[delimPosition+1:]
            return decode(output[:delimPosition])
          elif self.eof:
            self.finished = True
            if output == b"":
              raise StopIteration()
            else:
              return decode(output)
          else:
            self._readChunk()
      except StopIteration as ex:
        self._cleanUp()
        raise

    def __next__(self):
      if not self.returnedFirstLine:
        if self.firstLine is None:
          raise StopIteration()
        self.returnedFirstLine = True
        return self.firstLine
      return self._iterate()

