import pickle
import textwrap
import subprocess
import sys

class InterProcessTestFixture(object):
  def __init__(self, moduleName, tmpDirPath, modulesToImport=[]):
    self.moduleName = moduleName
    self.tmpDirPath = tmpDirPath
    self.modulesToImport = ["sys", "pickle"] + modulesToImport
  
  def startInNewProcess(self, code):
    fullCode = r"""
      import {0}
      from {1} import Fixture
      def compute(fixture):
        {2}
      
      fixture = Fixture(sys.argv[1])
      pickle.dump(compute(fixture), sys.stdout.buffer)"""
    fullCode = textwrap.dedent(fullCode).format(
        ", ".join(self.modulesToImport),
        self.moduleName, textwrap.indent(textwrap.dedent(code), "  "))

    return subprocess.Popen([sys.executable, "-c", fullCode, 
      self.tmpDirPath], stdout=subprocess.PIPE)

  def inNewProcess(self, code):
    stdout, _ = self.startInNewProcess(code).communicate()
    return pickle.loads(stdout)
