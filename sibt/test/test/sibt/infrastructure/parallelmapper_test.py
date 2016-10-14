import pytest
from sibt.infrastructure.parallelmapper import ParallelMapper

def test_shouldReturnMappedResultsAsAnIterable():
  mapper = ParallelMapper()
  assert list(mapper.map(lambda x: 2 * x, [1, 2, 3])) == [2, 4, 6]

def test_shouldThrowOccurredExceptionsWhenTheResultIsRetrieved():
  def mapFunc(x):
    if x == 1:
      return 12
    if x == 2:
      raise Exception("a")
    if x == 3:
      raise Exception("b")
  
  mapper = ParallelMapper()
  result = iter(mapper.map(mapFunc, [1, 2, 3]))

  assert next(result) == 12

  with pytest.raises(Exception) as ex:
    next(result)
  assert str(ex.value) == "a"

  with pytest.raises(Exception) as ex:
    next(result)
  assert str(ex.value) == "b"
