def iterableContainsInAnyOrder(iterable, *predicates):
  iterableAsList = list(iterable)
  if len(iterableAsList) != len(predicates):
    return False
  
  matchers = list(predicates)
  for x in iterableAsList:
    matchingMatchers = [matcher for matcher in matchers if matcher(x)]
    if len(matchingMatchers) == 0:
      return False
    matchers.remove(matchingMatchers[0])
    
  return True

def iterableContainsPropertiesInAnyOrder(iterable, propertyProducer, 
    *predicates):
  return iterableContainsInAnyOrder(map(propertyProducer, iterable),
      *predicates)

def equalsPred(expectedValue):
  return lambda arg: arg == expectedValue

class FakeException(Exception):
  def __init__(self, *args):
    super().__init__(*args)
