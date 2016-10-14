import pytest

from sibt.configuration.configurablelist import ConfigurableList, \
    LazyConfigurable
from sibt.configuration.exceptions import ConfigurableNotFoundException

def test_shouldLoadConfigurableOnceRequestedAndReturnTheResult():
  x = [2]
  def load():
    x[0] *= 2
    return x[0]

  confList = ConfigurableList([LazyConfigurable("foo", load)])
  assert confList.getByName("foo") == 4
  assert confList.getByName("foo") == 4

def test_shouldNotFindConfigurableIfLoadFunctionReturnsNone():
  confList = ConfigurableList([LazyConfigurable("foo", lambda: None)])
  with pytest.raises(ConfigurableNotFoundException):
    confList.getByName("foo")

def test_shouldLoadAllWhenIterating():
  x = [1]
  confList = ConfigurableList([
    LazyConfigurable("foo", lambda: x[0]),
    LazyConfigurable("bar", lambda: 2)])

  assert set(confList) == { 1, 2 }
  x[0] = 5
  assert set(confList) == { 1, 2 }
