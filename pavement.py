from paver.easy import *
import paver.doctools
from paver.setuputils import install_distutils_tasks
import sys

import pytest
import sys

ReadonlyConfigDir = "share/sibt/"
options(setup=dict(
    name="sibt",
    version="0.1",
    author="Patrick Plagwitz",
    author_email="patrick_plagwitz@web.de",
    packages=["sibt"],
    package_dir={"sibt": "sibt/src/sibt"}
#    data_files=[
#        (readonlyConfigDir + "schedulers", [
    ))
install_distutils_tasks()

def runPyTest(testFiles):
  pytest.main(["--color=yes"] + testFiles)

@task
def setup_pythonpath():
  sys.path += ["sibt/src", "sibt/schedulers"]
  
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
    

@task
@needs("generate_setup", "minilib", "setuptools.command.sdist")
def sdist():
  pass

@task
@needs("setuptools.command.install")
def install(options):
  print(options["install"].get("root", sys.prefix))
