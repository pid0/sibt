import fuse, stat, errno, sys

fuse.fuse_python_api = (0, 2)

class TestFS(fuse.Fuse):
  def __init__(self, *args, **kwargs):
    fuse.Fuse.__init__(self, *args, **kwargs)
    self.directories = ["/"]

  def getattr(self, path):
    if path in self.directories:
      return dirStatus()
    elif path.endswith("/fuse-file"):
      return regularFileStatus()
    else:
      return -errno.ENOENT

  def readdir(self, path, offset):
    entries = [".", "..", "fuse-file"]
    
    for entry in entries:
      yield fuse.Direntry(entry)

  def mkdir(self, path, mode):
    self.directories.append(path)

def dirStatus():
  return makeFileStatus(stat.S_IFDIR | 0o755, 2, 4096)
def regularFileStatus():
  return makeFileStatus(stat.S_IFREG | 0o666, 1, 0)

def makeFileStatus(mode, nlink, size):
  ret = fuse.Stat()
  ret.st_mode = mode
  ret.st_nlink = nlink
  ret.st_size = size
  ret.st_ino = ret.st_dev = 0
  ret.st_uid = 0
  ret.st_gid = 0
  ret.st_atime = ret.st_mtime = ret.st_ctime = 0
  return ret

if __name__ == "__main__":
  fs = TestFS()
  dontFork = ["-f"]
  fs.parse(args=sys.argv + dontFork, errex=1)
  fs.main()
