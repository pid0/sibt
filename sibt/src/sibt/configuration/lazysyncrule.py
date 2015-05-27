class LazySyncRule(object):
  def __init__(self, name, isEnabled, loadFunc):
    self.name = name
    self.enabled = isEnabled
    self.loadFunc = loadFunc

  def load(self):
    return self.loadFunc()
