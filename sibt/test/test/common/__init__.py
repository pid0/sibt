from py.path import local
import re

def relativeToProjectRoot(path):
  import sibt
  return str(local(sibt.__path__[0]) / ".." / ".." / ".." / path)
def relativeToTestRoot(path):
  import test
  return str(local(test.__path__[0]) / path)
