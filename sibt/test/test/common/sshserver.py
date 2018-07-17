import paramiko
import socket
import threading
import time
import subprocess
import functools
import queue
import tempfile
import py.path
import pytest
from datetime import datetime

import os

Port = 5123

LastSFTPHandler = None

@pytest.fixture(scope="module")
def sshServerFixture(request):
  serverSetup = SSHTestServerSetup.constructServer(
      py.path.local(tempfile.mkdtemp(
        prefix="sibt-ssh-", suffix="{0}:{1}".format(
        datetime.now().minute, datetime.now().second))), Port)
  serverSetup.server.start()
  request.addfinalizer(serverSetup.server.stop)
  return serverSetup

class ExecChannelHandler(threading.Thread):
  def __init__(self, commandProvider, channel, logFile, clientAddress, 
      transport, **kwargs):
    super().__init__(**kwargs)
    self._commandProvider = commandProvider
    self._channel = channel
    self.BufferSize = 2048
    self.ProcessFinished = lambda *_: None
    self.Nop = lambda *_: None
    self._logFile = logFile
    self._clientAddress = clientAddress
    self._transport = transport

  def _readStandardStream(self, readFunc, destQueue, sendFunc):
    try:
      for data in iter(functools.partial(readFunc, self.BufferSize), b""):
        destQueue.put((sendFunc, data))
    except:
      pass
    finally:
      destQueue.put((self.Nop, b""))

  def _waitForProcess(self, process, queueToPoison):
    process.wait()
    queueToPoison.put((self.ProcessFinished, b''))

  def run(self):
#    if not self._commandProvider.executionRequested.wait(0.5):
#      return
#
    self._logFile.write("{0}:{1} -- executing ‘{2}’\n".format(
      self._clientAddress, self._channel.get_id(), 
      self._commandProvider.commandToExecute))

    with subprocess.Popen(self._commandProvider.commandToExecute, shell=True, 
        bufsize=0, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE) as process:
      byteChunkQueue = queue.Queue()
      stdoutReader = threading.Thread(target=self._readStandardStream, 
          args=(process.stdout.read, byteChunkQueue, self._channel.sendall))
      stderrReader = threading.Thread(target=self._readStandardStream, 
          args=(process.stderr.read, byteChunkQueue, 
            self._channel.sendall_stderr))
      stdinReader = threading.Thread(target=self._readStandardStream, 
          args=(self._channel.recv, byteChunkQueue, process.stdin.write))
      processSentinel = threading.Thread(target=self._waitForProcess,
          args=(process, byteChunkQueue))
      stdoutReader.start()
      stderrReader.start()
      stdinReader.daemon = True
      stdinReader.start()
      processSentinel.start()

      while True:
        sendFunc, data = byteChunkQueue.get()
        if sendFunc is self.ProcessFinished or not self._transport.is_active():
          break
        try:
          sendFunc(data)
        except OSError:
          pass
      try:
        process.terminate()
      except:
        pass

    stdoutReader.join()
    stderrReader.join()
    processSentinel.join()
    while True:
      try:
        sendFunc, data = byteChunkQueue.get_nowait()
        sendFunc(data)
      except queue.Empty:
        break
      except OSError:
        pass
    self._channel.send_exit_status(process.returncode)

class ServerPolicy(paramiko.ServerInterface):
  def __init__(self, expectedClientKey):
    self._expectedClientKey = expectedClientKey
    self.executionRequested = threading.Event()
    self.commandToExecute = ""
    self.subsystemRequested = False

  def get_allowed_auths(self, userName):
    return "publickey"

  def check_auth_publickey(self, userName, key):
    return paramiko.AUTH_SUCCESSFUL if key == self._expectedClientKey else \
        paramiko.AUTH_FAILED

  def check_channel_request(self, kind, channelId):
    return paramiko.OPEN_SUCCEEDED if kind == "session" else \
        paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

  def check_channel_pty_request(self, channel, terminalType, widthInChars,
      heightInChars, widthInPixels, heightInPixels, modes):
    return True

  def check_channel_exec_request(self, channel, command):
    self.commandToExecute = command
    self.executionRequested.set()
    return True

  def check_channel_shell_request(self, channel):
    self.commandToExecute = "sh"
    self.executionRequested.set()
    return True

  def check_channel_subsystem_request(self, *args):
    self.subsystemRequested = True
    self.executionRequested.set()
    return super().check_channel_subsystem_request(*args)

class SFTPHandler(paramiko.SFTPServerInterface):
  def __init__(self, *args, logFile=None, **kwargs):
    super().__init__(*args, **kwargs)
    self._logFile = logFile
    global LastSFTPHandler
    LastSFTPHandler = self
    self.actions = []

  def _registerAction(self, *args):
    self.actions.append(args)

  def open(self, path, flags, attr):
    self._registerAction("open", path, flags, attr)
    return paramiko.SFTP_OP_UNSUPPORTED

  def list_folder(self, path):
    self._registerAction("list_folder", path)
    return paramiko.SFTP_OP_UNSUPPORTED

  def stat(self, path):
    self._registerAction("stat", path)
    return paramiko.SFTP_OP_UNSUPPORTED

  def lstat(self, path):
    self._registerAction("lstat", path)
    try:
      return paramiko.SFTPAttributes.from_stat(os.lstat(path))
    except OSError as ex:
      return paramiko.SFTPServer.convert_errno(ex.errno)

  def remove(self, path):
    self._registerAction("remove", path)
    return paramiko.SFTP_OP_UNSUPPORTED

  def rename(self, oldpath, newpath):
    self._registerAction("rename", oldpath, newpath)
    return paramiko.SFTP_OP_UNSUPPORTED

  def mkdir(self, path, attr):
    self._registerAction("mkdir", path, attr)
    return paramiko.SFTP_OP_UNSUPPORTED

  def rmdir(self, path):
    self._registerAction("rmdir", path)
    return paramiko.SFTP_OP_UNSUPPORTED

  def chattr(self, path, attr):
    self._registerAction("chattr", path, attr)
    return paramiko.SFTP_OP_UNSUPPORTED

  def readlink(self, path):
    self._registerAction("readlink", path)
    return paramiko.SFTP_OP_UNSUPPORTED
  
  def symlink(self, target_path, path):
    self._registerAction("symlink", target_path, path)
    return paramiko.SFTP_OP_UNSUPPORTED

class SSHTestServer(threading.Thread):
  def __init__(self, serverKey, expectedClientKey, port, logFile, **kwargs):
    super().__init__(**kwargs)
    self._key = serverKey
    self._expectedClientKey = expectedClientKey
    self._port = port
    self._stopping = False
    self._logFile = logFile

  def stop(self):
    self._stopping = True
    self.join()
    self._logFile.write("stopping\n")
    self._logFile.close()

  def _make_socket(self):
    addresses = socket.getaddrinfo("localhost", self._port, 
        type=socket.SOCK_STREAM)
    assert len(addresses) > 0

    sock = socket.socket(family=addresses[0][0], type=addresses[0][1])
    sock.settimeout(0.5)
    sock.bind(addresses[0][4])
    sock.listen(1)

    return sock

  def _enableSFTPSubsystem(self, transport):
    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, SFTPHandler,
        logFile=self._logFile)

  def _handleClient(self, clientSocket, clientAddress):
    with paramiko.Transport(clientSocket) as sshTransport:
      sshTransport.add_server_key(self._key)
      self._enableSFTPSubsystem(sshTransport)

      serverPolicy = ServerPolicy(self._expectedClientKey)
      sshTransport.start_server(event=None, server=serverPolicy)

      while sshTransport.is_active():
        channel = sshTransport.accept(1)
        if channel is None:
          break

        serverPolicy.executionRequested.wait()
        if serverPolicy.subsystemRequested:
          while sshTransport.is_active() and not self._stopping:
            time.sleep(0.2)
        else:
          with channel:
            handler = ExecChannelHandler(serverPolicy, channel, self._logFile, 
                clientAddress, sshTransport)
            handler.start()
            handler.join()

  def run(self):
    sock = self._make_socket()

    while not self._stopping:
      try:
        client, clientAddress = sock.accept()
      except socket.timeout:
        continue
      client.setblocking(True)

      clientThread = threading.Thread(target=self._handleClient, 
          args=(client, clientAddress))
      clientThread.name = "ssh-client-" + str(clientAddress)
      clientThread.start()

class SSHTestServerSetup(object):
  def __init__(self, server, knownHostsFile, clientIdFile, port):
    self.server = server
    self.knownHostsFile = knownHostsFile
    self.clientIdFile = clientIdFile
    self.port = port
    self.remoteShellCommand = "ssh -oUserKnownHostsFile={0} -i {1}".format(
        self.knownHostsFile, self.clientIdFile)

  @classmethod
  def constructServer(clazz, folder, port):
    clientKey = paramiko.rsakey.RSAKey.generate(2048)
    clientIdFile = str(folder / "id_rsa")
    clientKey.write_private_key_file(clientIdFile)

    serverKey = paramiko.rsakey.RSAKey.generate(2048)

    hostKeys = paramiko.hostkeys.HostKeys()
    hostKeys.add("[localhost]:{}".format(port), "ssh-rsa", serverKey)
    mockSSHFolder = folder / ".ssh"
    mockSSHFolder.mkdir()
    knownHostsFile = str(mockSSHFolder / "known_hosts")
    hostKeys.save(knownHostsFile)

    logFile = open(str(folder / "log"), "w")
    server = SSHTestServer(serverKey, clientKey, port, logFile)

    return clazz(server, knownHostsFile, clientIdFile, port)

if __name__ == "__main__":
  import sys, time, logging
  logging.basicConfig()
  logging.getLogger("paramiko").setLevel(logging.DEBUG)
  logging.getLogger("paramiko.transport").setLevel(logging.DEBUG)

  if len(sys.argv) < 2:
    sys.stderr.write("<server folder>\n")
    sys.exit(2)

  serverSetup = SSHTestServerSetup.constructServer(py.path.local(sys.argv[1]), 
      Port)
  serverSetup.server.start()
  while True:
    try:
      time.sleep(0.5)
    except KeyboardInterrupt:
      serverSetup.server.stop()
      print(LastSFTPHandler.actions)
      sys.exit()
