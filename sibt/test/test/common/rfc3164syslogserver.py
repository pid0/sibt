from socketserver import UDPServer, BaseRequestHandler
from threading import Thread
from collections import namedtuple
import time
import re

PacketRegex = re.compile(
    rb"^<(?P<priority>\d+)>"
    rb"(?P<timestamp>[\w: ]{15}) "
    rb"(?P<hostname>\w+) "
    rb"(?P<tag>\w+)\["
    rb"(?P<pid>\d+)\]: "
    rb"(?P<message>.*)$")

FacilityNames = [
    "kern",
    "user",
    "mail",
    "daemon"]
SeverityNames = [
    "emerg",
    "alert",
    "crit",
    "err",
    "warning",
    "notice",
    "info",
    "debug"]

SyslogPacket = namedtuple("SyslogPacket", [
    "facility", "severity", "tag", "message"])

class _Handler(BaseRequestHandler):
  def handle(self):
    packetContent, _ = self.request
    self.server.packets.append(self._parsePacket(packetContent))

  def _parsePacket(self, data):
    match = PacketRegex.match(data)
    if match is None:
      raise Exception("wrong format in syslog packet:\n" + data.decode())

    priority, tag, message = match.group("priority", "tag", "message")
    return SyslogPacket(*self._decodePriority(int(priority)), tag, message)

  def _decodePriority(self, priority):
    facility = (priority & (~7)) >> 3
    severity = priority & 7

    return FacilityNames[facility], SeverityNames[severity]

class _Server(UDPServer):
  def __init__(self, packetList, *args):
    super().__init__(*args)
    self.packets = packetList

class Rfc3164SyslogServer(object):
  def __init__(self, port):
    self.port = port
    self.packets = []

  def _operateServer(self):
    self.server.serve_forever(poll_interval=0.1)

  def __enter__(self):
    self.server = _Server(self.packets, ("localhost", self.port), _Handler)

    self.thread = Thread(target=self._operateServer)
    self.thread.start()

    return self

  def __exit__(self, exceptionType, ex, traceback):
    self.server.shutdown()
    self.thread.join()
    self.server.server_close()


if __name__ == "__main__":
  try:
    with Rfc3164SyslogServer(5000) as server:
      time.sleep(30)
  except KeyboardInterrupt:
    pass

  for packet in server.packets:
    print(packet)
