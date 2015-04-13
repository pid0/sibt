import subprocess
from sibt.infrastructure.exceptions import ExternalFailureException

ChunkSize = 2048

class CoprocessRunner(object):
  def _wrappingException(self, func):
    try:
      return func()
    except subprocess.CalledProcessError as ex:
      raise ExternalFailureException(ex.cmd[0], ex.cmd[1:], 
          ex.returncode) from ex
    
  def getOutput(self, program, *arguments, delimiter="\n"):
    assert ord(delimiter) < 128
    process = subprocess.Popen([program] + list(arguments),
        stdout=subprocess.PIPE)

    return CoprocessRunner.OutputIterator([program] + list(arguments), 
        process, delimiter.encode("utf-8"))

  def execute(self, program, *arguments):
    return self._wrappingException(lambda: 
        subprocess.check_call([program] + list(arguments)))


  class OutputIterator(object):
    def __init__(self, arguments, process, delimiter):
      self.arguments = arguments
      self.process = process
      self.delimiter = delimiter
      self.stdout = process.stdout
      self.finished = False
      self.returnedFirstLine = False
      self.firstLine = None
      self.buffer = b""
      self.eof = False

      self._waitForFirstLine()

    def _waitForFirstLine(self):
      try:
        self.firstLine = self._iterate()
      except StopIteration:
        pass

    def _cleanUp(self):
      self.process.wait()
      with self.process:
        pass
      if self.process.poll() != 0:
        raise ExternalFailureException(self.arguments[0], 
            self.arguments[1:], self.process.returncode)

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
            return output[:delimPosition].decode()
          elif self.eof:
            self.finished = True
            if output == b"":
              raise StopIteration()
            else:
              return output.decode()
          else:
            self._readChunk()
      except Exception as ex:
        self._cleanUp()
        raise

    def __next__(self):
      if not self.returnedFirstLine:
        if self.firstLine is None:
          raise StopIteration()
        self.returnedFirstLine = True
        return self.firstLine
      return self._iterate()

