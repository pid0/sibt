import signal

class SigHandler(object):
  def __init__(self, signalNumber, handlerFunc):
    self.signalNumber = signalNumber
    self.handlerFunc = handlerFunc

  def __enter__(self):
    self.originalHandler = signal.signal(self.signalNumber, self.handlerFunc)
    return self

  def __exit__(self, x, y, z):
    signal.signal(self.signalNumber, self.originalHandler)
