from py.path import local
import re

def relativeToProjectRoot(path):
  import sibt
  return str(local(sibt.__path__[0]) / ".." / ".." / ".." / path)

def unIndentCode(code):
  lines = [line for line in code.splitlines() if len(line.strip()) > 0]
  spacePrefixLengths = [len(re.match(r"([ ]*)[^ ]", line).group(1)) for 
      line in lines]
  longestCommonPrefix = min(spacePrefixLengths, default=0)
  return "\n".join(line[longestCommonPrefix:] for line in lines)
