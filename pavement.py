# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from paver.easy import *
import paver.doctools
from paver.setuputils import install_distutils_tasks, find_packages
import sys
import shutil

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
    license="GNU General Public License v3 (GPLv3)",
    description="Configurable command line interface to backup tools",

    version="0.2.1",

    packages=find_packages("sibt/src"),
    package_dir={"sibt": "sibt/src/sibt", "test": "sibt/test/test"},

#    entry_points={
#        "console_scripts": ["sibt = sibt.main:main"]
#    },

    scripts=["sibt/sibt"],

    data_files=[
        (ReadonlyConfigDir + "schedulers", [
          "sibt/schedulers/anacron",
          "sibt/schedulers/simple"]),

        (ReadonlyConfigDir + "synchronizers", [
          "sibt/synchronizers/null",
          "sibt/synchronizers/rdiff-backup",
          "sibt/synchronizers/rsync",
          "sibt/synchronizers/tar"]),

        (ReadonlyConfigDir + "runners", [
          "sibt/runners/bash-runner"]),

        (ReadonlyConfigDir + "include", [
          "sibt/include/TarFullSystemBackup.inc"])
    ]
    ))
    # test_requires = "pytest"
install_distutils_tasks()

def runPyTest(testFiles):
  pytest.main(["--color=yes", "-v"] + testFiles)

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
  prependToPythonPath(os.path.abspath("sibt/test"))

  if "LC_ALL" in os.environ:
    del os.environ["LC_ALL"]
  os.environ["LC_MESSAGES"] = "C"

  testTempDir = local(tempfile.gettempdir()) / "sibt-test-temp-dir"
  if os.path.isdir(str(testTempDir)):
    shutil.rmtree(str(testTempDir))
  testTempDir.mkdir()
  testTempDir.chdir()
  
@task
@needs(["setup_testing"])
def quick_acceptance_test():
  runPyTest([str(Root / "sibt/test/test/acceptance/sibtspec.py")])
  runPyTest([str(Root / "sibt/test/test/acceptance/schedulerusagespec.py")])

@task
@needs(["quick_acceptance_test"])
def acceptance_test():
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
