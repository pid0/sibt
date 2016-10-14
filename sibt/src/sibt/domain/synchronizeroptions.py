import collections

class SynchronizerOptions(collections.UserDict):
  def __init__(self, options, locOptions):
    self.options = options
    self.locOptions = locOptions
    super().__init__(dict(list(options.items()) + 
      list(zip(self.locKeys, self.locOptions))))

    self.locs = locOptions

  def withNewLocs(self, newLocs):
    return SynchronizerOptions(self.options, newLocs)

  @property
  def locKeys(self):
    return ["Loc" + str(i + 1) for i, _ in enumerate(self.locOptions)]

  @classmethod
  def fromDict(clazz, options):
    normalOpts = dict(options)
    locKeys = [name for name in options.keys() if name.startswith("Loc") and
        all(c.isdigit() for c in name[3:])]
    locKeys.sort(key=lambda locKey: int(locKey[3:]))

    locValues = []
    for locKey in locKeys:
      locValues.append(options[locKey])
      del normalOpts[locKey]
    return clazz(normalOpts, locValues)

  def loc(self, i):
    return self.locs[i - 1]

  def __eq__(self, other):
    if not (hasattr(other, "options") and hasattr(other, "locOptions")):
      return False
    return other.options == self.options and other.locOptions == self.locOptions

  def __repr__(self):
    return "SynchronizerOptions{0}".format((self.options, self.locOptions))
