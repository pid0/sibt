import tempfile
import functools
import os

from sibt.application.locationformatter import locToSSHFSArgs
from sibt.domain.optioninfo import OptionInfo
from sibt.domain.port import Port
from sibt.infrastructure import types
from sibt.infrastructure.location import LocalLocation

AvailableOptions = [
    OptionInfo("RemoteShellCommand", types.String)]

_FileMountPoint = object()

def isExtensible(syncer):
  def protocolsSuitable(protocols):
    return "ssh" not in protocols and "file" in protocols

  return all(protocolsSuitable(port.supportedProtocols) for 
      port in syncer.ports)

class SSHFSAutoMountingSynchronizer(object):
  def __init__(self, wrapped, processRunner):
    if not isExtensible(wrapped):
      raise ValueError("synchronizer is not extensible with SSHFS")

    self._wrapped = wrapped
    self._processRunner = processRunner
    self.availableOptions = wrapped.availableOptions + AvailableOptions
    self.ports = [port.withAdditionalProtocols("ssh") for port in wrapped.ports]

  def _forEachMountPoint(self, func, remoteLocs, mountPoints):
    for mountPoint, loc in zip(mountPoints, remoteLocs):
      if mountPoint is _FileMountPoint:
        continue
      func(mountPoint, loc)

  def _mount(self, remoteShellCommand, mountPoint, sshLoc):
    args = locToSSHFSArgs(sshLoc)
    args += [mountPoint]
    if remoteShellCommand is not None:
      args += ["-o", "ssh_command=" + remoteShellCommand]

    self._processRunner.execute("sshfs", *args)

  def _unmount(self, mountPoint, _):
    self._processRunner.execute("fusermount", "-u", mountPoint)
    os.rmdir(mountPoint)
    os.rmdir(os.path.dirname(mountPoint))

  def _replaceWithMountPoints(self, options, mountPoints):
    newLocs = [LocalLocation(mountPoint) if mountPoint is not _FileMountPoint
        else loc for mountPoint, loc in zip(mountPoints, options.locOptions)]
    return options.withNewLocs(newLocs)

  def _makeMountPoints(self, options):
    ret = []
    for loc in options.locs:
      if loc.protocol == "ssh":
        tempDir = tempfile.mkdtemp(prefix="sibt-sshfs-mount")
        mountPoint = os.path.join(tempDir, "mount")
        os.mkdir(mountPoint)
        ret.append(mountPoint)
      else:
        ret.append(_FileMountPoint)

    return ret

  def _executeWhileMounted(self, func, options, args):
    mountPoints = self._makeMountPoints(options)
    self._forEachMountPoint(
        functools.partial(self._mount, options.get("RemoteShellCommand", None)),
        options.locOptions, mountPoints)
    try:
      ret = func(self._replaceWithMountPoints(options, mountPoints), *args)
    finally:
      self._forEachMountPoint(self._unmount, options.locOptions, mountPoints)
    return ret

  def versionsOf(self, options, *args):
    return self._executeWhileMounted(self._wrapped.versionsOf, options, args)
  def listFiles(self, options, *args):
    return self._executeWhileMounted(self._wrapped.listFiles, options, args)
  def sync(self, options, *args):
    return self._executeWhileMounted(self._wrapped.sync, options, args)
  def restore(self, options, *args):
    return self._executeWhileMounted(self._wrapped.restore, options, args)

  def __getattr__(self, name):
    return getattr(self._wrapped, name)
