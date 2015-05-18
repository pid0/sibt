class OptionInfo(object):
  def __init__(self, name, optionType):
    self.name = name
    self.optionType = optionType

  def __str__(self):
    return self.name

  def __repr__(self):
    return "OptionInfo{0}".format((self.name, self.optionType))
