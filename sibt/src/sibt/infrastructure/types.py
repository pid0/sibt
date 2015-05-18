class Enum(object):
  class Value(object):
    def __init__(self, name, equatableToNames):
      self.name = name
      self.equatableToNames = equatableToNames

    def __str__(self):
      return self.name

    def __repr__(self):
      return "Enum.Value({0})".format(repr(self.name))

    def __eq__(self, other):
      if self.equatableToNames:
        return self.name == other or self is other
      return self is other

  def __init__(self, *elementNames, equatableToNames=False):
    elements = [Enum.Value(name, equatableToNames) for name in elementNames]
    self.values = elements

    for name, element in zip(elementNames, elements):
      fieldName = name
      if name == "None":
        fieldName += "_"
      setattr(self, fieldName, element)

String = object()
Bool = object()
TimeDelta = object()
File = object()
Positive = object()

Location = object()
