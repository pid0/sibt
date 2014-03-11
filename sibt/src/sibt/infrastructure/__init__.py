import os
import os.path

def collectFilesInDirs(dirs, visitor):
  ret = set()
  for directory in dirs:
    if os.path.isdir(directory):
      for fileName in os.listdir(directory):
        path = os.path.join(directory, fileName)
        if not os.path.isfile(path):
          continue
        result = visitor(path, fileName)
        if result is not None:
          ret |= {result}

  return ret
