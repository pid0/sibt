from sibt.formatstringrulesinterpreter import FormatStringRulesInterpreter
from test.common.executionlogger import ExecutionLogger
from test.common.rulebuilder import anyRule

import pytest

class Fixture(object):
  def __init__(self):
    self.toolRunner = ExecutionLogger()
  
  def executedPrograms(self):
    return self.toolRunner.programsList
  
  executedPrograms = property(executedPrograms)

@pytest.fixture
def fixture():
  return Fixture()

def test_shouldReadStringAsShellCmdAndReplaceDestAndSrcWithRespectiveRuleDirs(
  fixture):
  interpreter = FormatStringRulesInterpreter(
    "program {dest} arg {src} anotherarg", identity)
  
  source = "/replaces/src"
  dest = "/replaces/dest"
  
  interpreter.processRule(anyRule().
    withSource(source).
    withDest(dest).build(), fixture.toolRunner)
  
  assert fixture.executedPrograms == [("program", (dest, 
    "arg", source, "anotherarg"))]
  
def test_shouldApplyTransformerFunctionToSourceDir(fixture):
  sourceDir = "/source/dir"
  transformedSourceDir = "/tranformed/source"
  
  interpreter = FormatStringRulesInterpreter("backupprogram {src}",
    lambda source: transformedSourceDir if source == sourceDir else "any")
  
  interpreter.processRule(anyRule().withSource(sourceDir).build(),
    fixture.toolRunner)
  
  assert fixture.executedPrograms == [("backupprogram", 
    (transformedSourceDir, ))]
  
def identity(x):
  return x