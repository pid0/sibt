class Enum(object):
  class _Value(object):
    def __init__(self, name):
      self.name = name

    def __str__(self):
      return self.name

    def __repr__(self):
      return "Enum._Value({0})".format(repr(self.name))

  values = []

  @classmethod
  def value(clazz, name):
    fieldName = name
    if name == "None":
      fieldName += "_"
    value = Enum._Value(name)
    setattr(clazz, fieldName, value)
    clazz.values.append(value)
