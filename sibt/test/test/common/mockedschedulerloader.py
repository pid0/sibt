class MockedSchedulerLoader(object):
  def __init__(self, namesToSchedulers):
    self.namesToSchedulers = namesToSchedulers

  def loadFromFile(self, path, name, initArgs):
    return self.namesToSchedulers[name]

