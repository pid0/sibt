from test.common import relativeToTestRoot
import subprocess
import signal
import time

ScriptPath = relativeToTestRoot("acceptance/mount-fuse-fs.py")

class FuseFS(object):
  def __init__(self, mountPoint):
    self.process = None
    self.mountPoint = mountPoint

  def __enter__(self):
    self.process = subprocess.Popen(["python2", ScriptPath, 
      "-o", "nonempty", self.mountPoint])
    time.sleep(0.05)
    return self

  def __exit__(self, exceptionType, ex, traceback):
    self.unmount()

  def unmount(self):
    self.process.send_signal(signal.SIGTERM)
    self.process.wait()

def nonEmptyFSMountedAt(mountPoint):
  return FuseFS(str(mountPoint))

def fuseIsAvailable():
  return subprocess.run(["python2", "-c", "import fuse"]).returncode == 0
