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

import pytest
from sibt.infrastructure.coprocessrunner import \
    CoprocessRunner
from sibt.infrastructure.exceptions import ExternalFailureException
from test.common.assertutil import strToTest, FakeException
import sys

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.runner = CoprocessRunner()
    self.counter = 0

  def writeBashExecutable(self, code):
    self.counter += 1
    path = self.tmpdir.join("script-{0}".format(self.counter))
    path.write("#!/usr/bin/env bash\n" + code)
    path.chmod(0o700)
    return str(path)

@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

@pytest.mark.parametrize("arg", ["leave-off-last-null", ""])
def test_shouldReturnIteratorContainingTheLinesSplitAtSpecifiedChar(arg, 
    fixture):
  path = fixture.writeBashExecutable(r"""
      echo -n -e ' foo\0'
      echo -n bar; if [ "$1" != leave-off-last-null ]; then 
        echo -n -e '\0'; fi""")

  assert list(fixture.runner.getOutput(path, arg, delimiter="\0")) == \
      [" foo", "bar"]

def test_shouldWorkInAllTimingDependentCircumstances(fixture):
  path = fixture.writeBashExecutable(r"echo -n -e 'a\nb\n'")

  assert list(fixture.runner.getOutput(path)) == ["a", "b"]

  path = fixture.writeBashExecutable(r"""for i in $(seq 5000); do 
    echo -n 12345
  done 
  echo""")

  assert list(fixture.runner.getOutput(path)) == [5000 * "12345"]

def test_shouldReturnEmptyIteratorForNoOutput(fixture):
  path = fixture.writeBashExecutable("")

  assert list(fixture.runner.getOutput(path)) == []

def test_shouldRaiseCustomExceptionIfProgramReturnsWithNonZeroStatus(fixture):
  path = fixture.writeBashExecutable(r"""
      echo out
      sleep 0.1
      exit 103""")

  with pytest.raises(ExternalFailureException) as ex:
    list(fixture.runner.getOutput(path))
  assert ex.value.exitStatus == 103
  with pytest.raises(ExternalFailureException) as ex:
    fixture.runner.execute(path, "a", "b")
  assert ex.value.program == path
  assert ex.value.arguments == ["a", "b"]

def test_shouldRaiseExceptionDuringGetOutputCallIfProgramFailsWithoutOutput(
    fixture):
  path = fixture.writeBashExecutable(r"exit 54")

  with pytest.raises(ExternalFailureException) as ex:
    fixture.runner.getOutput(path)
  assert ex.value.exitStatus == 54

def test_shouldCallFuncsAfterForkingANewProcessAndAfterItsTermination(fixture, 
    capfd):
  raiseException = False
  def before():
    sys.stderr.write("before\n")
  def after(exitStatus):
    sys.stderr.write(str(exitStatus) + "\n")
    if raiseException:
      raise FakeException()

  runner = CoprocessRunner(before, after)

  def shouldOutputInCorrectOrder(runFunc, exitStatus):
    path = fixture.writeBashExecutable(r"echo foo >&2; exit " + str(exitStatus))
    if raiseException:
      with pytest.raises(FakeException):
        runFunc(path)
    else:
      runFunc(path)
    _, stderr = capfd.readouterr()
    strToTest(stderr).shouldContainLinePatternsInOrder("before", "foo", 
        str(exitStatus))

  shouldOutputInCorrectOrder(runner.execute, 0)
  raiseException = True
  shouldOutputInCorrectOrder(runner.getOutput, 5)
