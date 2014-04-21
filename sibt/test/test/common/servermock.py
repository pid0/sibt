import socket
from threading import Thread

class ServerMock(object):
  def __init__(self, port, socketType):
    self.port = port
    self.socketType = socketType
    self.sock = None
    self.closing = False

  def _operateSocket(self):
    self.receivedBytes = b""

    while not self.closing:
      if self.socketType == socket.SOCK_DGRAM:
        self.receivedBytes += self.sock.recv(2**12)

    self.sock.close()

  def __enter__(self):
    addrinfo = socket.getaddrinfo("localhost", self.port,
        type=self.socketType)[0]
    self.sock = socket.socket(family=addrinfo[0], 
        type=addrinfo[1])
    self.sock.settimeout(0.3)
    self.sock.bind(addrinfo[4])
    
    if self.socketType != socket.SOCK_DGRAM:
      self.sock.listen(1)

    self.thread = Thread(target=self._operateSocket)
    self.thread.start()

    return self

  def __exit__(self, exceptionType, ex, traceback):
    self.closing = True
    self.thread.join()

  def println(self, x):
    self.newFile.write(x + os.linesep)

