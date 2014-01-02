from paver.easy import *
import paver.doctools
from paver.setuputils import setup

import pytest
import sys

setup(name="sibt",
  packages=["sibt"],
  version="0.1",
  author="Patrick Plagwitz",
  author_email="patrick_plagwitz@web.de")

def runPyTest(testFiles):
  pytest.main(["--color=yes"] + testFiles)

@task
def setup_pythonpath():
  sys.path += ["sibt/src"]
  
@task
@needs(["setup_pythonpath"])
def acceptance_test():
  runPyTest(["sibt/test/test/acceptance/sibtspec.py"])
@task
@needs(["setup_pythonpath"])
def unit_test():
  runPyTest(["sibt/test/test/sibt"])
@task
@needs(["setup_pythonpath"])
@consume_args
def test_only(args):
  runPyTest(args)

@task
@consume_args
@needs(["acceptance_test", "unit_test"])
def test(args):
  pass
    
