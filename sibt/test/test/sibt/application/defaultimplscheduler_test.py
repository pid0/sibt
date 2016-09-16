from test.common.builders import anyScheduling, mockSched, execEnvironment
from sibt.application.defaultimplscheduler import DefaultImplScheduler
from test.common import mock

def test_shouldCallRunSynchronizerWhenExecutedAsADefault():
  returnedObject = object()
  execEnv = mock.mock()
  execEnv.expectCalls(mock.call("runSynchronizer", (), ret=returnedObject))

  schedWithoutExecute = object()
  scheduler = DefaultImplScheduler(schedWithoutExecute)

  assert scheduler.execute(execEnv, anyScheduling()) is returnedObject

def test_shouldCallTheWrappedSchedsExecuteMethodIfItHasOne():
  wrappedSched = mock.mock()
  execEnv, scheduling, returnedObject = object(), object(), object()

  wrappedSched.expectCalls(mock.call("execute", (execEnv, scheduling), 
    ret=returnedObject))

  assert DefaultImplScheduler(wrappedSched).execute(execEnv, scheduling) is \
      returnedObject
