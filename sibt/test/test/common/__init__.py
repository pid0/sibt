from py.path import local
import re

def relativeToProjectRoot(path):
  import sibt
  return str(local(sibt.__path__[0]) / ".." / ".." / ".." / path)
