def iterableContainsInAnyOrder(iterable, *predicates):
  if len(iterable) != len(predicates):
    return False
  
  matchers = list(predicates)
  for x in iterable:
    matchingMatchers = [matcher for matcher in matchers if matcher(x)]
    if len(matchingMatchers) == 0:
      return False
    matchers.remove(matchingMatchers[0])
    
  return True
