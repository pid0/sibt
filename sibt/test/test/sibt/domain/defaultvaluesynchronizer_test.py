from test.common.builders import fakeConfigurable, port, optInfo, \
    location as loc
from sibt.domain.defaultvaluesynchronizer import DefaultValueSynchronizer
from test.common.assertutil import iterToTest
from sibt.infrastructure import types

def test_shouldAddLocOptInfosToAvailableOptionsBasedOnPorts():
  wrapped = fakeConfigurable("syncer", 
      ports=[port(), port(), port()], availableOptions=[])
  syncer = DefaultValueSynchronizer(wrapped)

  iterToTest(syncer.availableOptions).shouldContainMatching(
      lambda opt: opt.name == "Loc1" and opt.optionType == types.Location,
      lambda opt: opt.name == "Loc2", lambda opt: opt.name == "Loc3")
