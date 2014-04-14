import os
import os.path

def collectFilesInDirs(dirs, visitor):
  ret = set()
  for directory in dirs:
    absDir = os.path.abspath(directory)
    if os.path.isdir(absDir):
      for fileName in os.listdir(absDir):
        path = os.path.join(absDir, fileName)
        if not os.path.isfile(path) or fileName.startswith("."):
          continue
        result = visitor(path, fileName)
        if result is not None:
          ret |= {result}

  return ret
