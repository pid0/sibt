from paver.easy import *
import paver.doctools
from paver.setuputils import install_distutils_tasks, find_packages
import sys

import pytest
import sys

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
        (ReadonlyConfigDir + "interpreters", 
            ["sibt/interpreters/rdiff-backup"]),
        (ReadonlyConfigDir + "runners", ["sibt/runners/bash-runner"])
    ]
    ))
    # test_requires = "pytest >= 2.5"
install_distutils_tasks()

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
def integration_test():
  runPyTest(["sibt/test/test/integration"])

@task
@needs(["setup_pythonpath"])
@consume_args
def test_only(args):
  runPyTest(args)

@task
@consume_args
@needs(["acceptance_test", "unit_test", "integration_test"])
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
