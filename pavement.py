from paver.easy import *
import paver.doctools
from paver.setuputils import install_distutils_tasks, find_packages
import sys

import pytest
import os
import tempfile
from py.path import local

Root = (local(os.path.abspath(".")) / __file__).dirpath()
PreviousCwd = local(os.getcwd())
ReadonlyConfigDir = "share/sibt/"
options(setup=dict(
    name="sibt",
    author="Patrick Plagwitz",
    author_email="patrick_plagwitz@web.de",
    #license="GNU General Public License v3 (GPLv3)",
    description="Configurable command line interface to backup tools",

    version="0.1",

    packages=find_packages("sibt/src"),
    package_dir={"sibt": "sibt/src/sibt", "test": "sibt/test/test"},
#    entry_points={
#        "console_scripts": ["sibt = sibt.main:main"]
#    },
    scripts=["sibt/sibt"],

    data_files=[
        (ReadonlyConfigDir + "schedulers", ["sibt/schedulers/anacron"]),
        (ReadonlyConfigDir + "synchronizers", 
            ["sibt/synchronizers/rdiff-backup"]),
        (ReadonlyConfigDir + "runners", ["sibt/runners/bash-runner"])
    ]
    ))
    # test_requires = "pytest"
install_distutils_tasks()

def runPyTest(testFiles):
  pytest.main(["--color=yes"] + testFiles)

def prependToPythonPath(newPath):
  envVarName = "PYTHONPATH"

  if envVarName in os.environ:
    os.environ[envVarName] = newPath + ":" + os.environ[envVarName]
  else:
    os.environ[envVarName] = newPath

  sys.path = [newPath] + sys.path

@task
def setup_testing():
  prependToPythonPath(os.path.abspath("sibt/src"))
  testTempDir = local(tempfile.gettempdir()) / "sibt-test-temp-dir"
  if not os.path.isdir(str(testTempDir)):
    testTempDir.mkdir()
  testTempDir.chdir()
  
@task
@needs(["setup_testing"])
def acceptance_test():
  runPyTest([str(Root / "sibt/test/test/acceptance/sibtspec.py")])
  runPyTest([str(Root / "sibt/test/test/acceptance/processspec.py")])

@task
@needs(["setup_testing"])
def unit_test():
  runPyTest([str(Root / "sibt/test/test/sibt")])

@task
@needs(["setup_testing"])
def test_test():
  runPyTest([str(Root / "sibt/test/test/common")])

@task
@needs(["setup_testing"])
def integration_test():
  runPyTest([str(Root / "sibt/test/test/integration")])

@task
@needs(["setup_testing"])
@consume_args
def test_only(args):
  testFiles = [str(PreviousCwd / arg) for arg in args]
  if args[0] == "--pdb":
    import pdb
    pdb.runcall(runPyTest, testFiles[1:])
  else:
    runPyTest(testFiles)

@task
@consume_args
@needs(["acceptance_test", "unit_test", "integration_test", "test_test"])
def test(args):
  pass
    

@task
@needs("generate_setup", "minilib", "setuptools.command.sdist")
def sdist():
  pass

#@task
#@needs("setuptools.command.install")
#def install(options):
#  print(options["install"].get("root", sys.prefix))
