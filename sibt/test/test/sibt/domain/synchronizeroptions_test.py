from sibt.domain.synchronizeroptions import SynchronizerOptions as SyncerOpts
from collections import OrderedDict

def test_shouldImplementEquals():
  assert SyncerOpts({"A": 2}, ["/tmp"]) == SyncerOpts({"A": 2}, ["/tmp"])
  assert SyncerOpts({"A": 2}, ["/tmp"]) != {"A": 2, "Loc1": "/tmp"}

def test_shouldProvideAccessToLocOptionsThroughDictLikeInterface():
  opts = SyncerOpts({"Opt": False}, ["/mnt", "/tmp"])

  assert opts["Loc1"] == "/mnt"
  assert opts["Loc2"] == "/tmp"

  assert dict(opts) == {"Opt": False, "Loc1": "/mnt", "Loc2": "/tmp"}

  assert set([key for key in opts]) == {"Opt", "Loc1", "Loc2"}

def test_shouldHaveFactoryFuncThatTakesADict():
  optDict = OrderedDict()
  optDict["Loc2"] = "/bar"
  optDict["Loc1"] = "/foo"
  assert SyncerOpts.fromDict(optDict) == SyncerOpts({}, ["/foo", "/bar"])
