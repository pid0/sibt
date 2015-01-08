import os.path

def removeCommonPrefix(path, containerPath):
  normalizedPath = os.path.realpath(path)
  normalizedContainer = os.path.realpath(containerPath)
  startIndex = normalizedPath.index(normalizedContainer)
  return os.path.normpath(normalizedPath[startIndex + 
      len(normalizedContainer) + 1:])

def isPathWithinPath(path, container):
  normalizedContainer = os.path.realpath(container)
  normalizedPath = os.path.realpath(path)
  commonPart = os.path.commonprefix([normalizedPath, normalizedContainer])
  return commonPart == normalizedContainer and \
      ((normalizedPath[len(commonPart):] + "/")[0] == os.path.sep)

