import os

def collectFilesInDirs(dirs, visitor):
  ret = set()
  for directory in dirs:
    for fileName in os.listdir(directory):
      result = visitor(directory + "/" + fileName, fileName)
      if result is not None:
        ret |= {result}

  return ret
