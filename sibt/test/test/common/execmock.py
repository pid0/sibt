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

from test.common import mock
from sibt.infrastructure.exceptions import ExternalFailureException

DontCheck = object()

def call(*args, **kwargs):
  return (args, kwargs)

def matcherThrowingNotImplementedFailure(predicate):
  def ret(program, args, delimiter="\n"):
    if predicate(program, args, delimiter):
      raise ExternalFailureException("", (), 200)
    return False
  return ret

def makeMockCall(program, predicateOrTuple, ret=[], delimiter="\n", 
    returningNotImplementedStatus=False, **otherKwargs):
  expectedDelimiter = delimiter
  matcher = (lambda calledProgram, args, delimiter="\n": 
      calledProgram == program and
      (predicateOrTuple(args) if callable(predicateOrTuple) else 
        args == predicateOrTuple) and 
      (delimiter == expectedDelimiter or expectedDelimiter is DontCheck)) 

  return mock.callMatching("getOutput", 
      matcherThrowingNotImplementedFailure(matcher) if \
          returningNotImplementedStatus else matcher, 
          ret=ret, **otherKwargs)

def withAnyNumberIsTrue(kwargs):
  ret = dict(kwargs)
  ret["anyNumber"] = True
  return ret

class ExecMock(object):
  def __init__(self):
    self.reset()

  def reset(self):
    self.mockedExec = mock.mock("ExecMock")
    self.returningNotImplementedStatuses = False

  def expect(self, program, *calls, anyOrder=False):
    self.mockedExec.expectCalls(*[makeMockCall(program, *call[0], **call[1]) 
      for call in calls], inAnyOrder=anyOrder)
  def allow(self, program, *calls):
    self.mockedExec.expectCalls(*[makeMockCall(program, *call[0], 
      **withAnyNumberIsTrue(call[1])) for call in calls], inAnyOrder=True)

  def execute(self, program, *arguments):
    self.getOutput(program, *arguments)
  def getOutput(self, program, *arguments, delimiter="\n"):
    if self.returningNotImplementedStatuses:
      raise ExternalFailureException("", (), 200)
    return self.mockedExec.getOutput(program, arguments, delimiter=delimiter)

  def check(self):
    self.mockedExec.checkExpectedCalls()
