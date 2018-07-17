import subprocess

CountingPort = 5124

class DAVServer:
  def __init__(self, path, port):
    self.port = port
    self.chezdav = subprocess.Popen(
        ["chezdav", "--port", str(port), "--path", path])

  @classmethod
  def start(clazz, path):
    global CountingPort
    port = CountingPort
    CountingPort += 1
    return clazz(path, port)

  def stop(self):
    self.chezdav.terminate()
