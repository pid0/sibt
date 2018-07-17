# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    time.sleep(0.1)
    return self

  def __exit__(self, exceptionType, ex, traceback):
    self.unmount()

  def unmount(self):
    self.process.send_signal(signal.SIGTERM)
    self.process.wait()

def nonEmptyFSMountedAt(mountPoint):
  return FuseFS(str(mountPoint))

def fuseIsAvailable():
  return subprocess.call(["python2", "-c", "import fuse"]) == 0
