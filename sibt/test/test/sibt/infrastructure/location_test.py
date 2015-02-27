import pytest
from sibt.infrastructure.location import LocalLocation
from sibt.domain.exceptions import LocationInvalidException

class Test_LocalLocationTest(object):
  def test_shouldNormalizeThePathWithoutChangingItsMeaning(self):
    assert str(LocalLocation("//tmp///test/link/../foo//")) == \
        "/tmp/test/link/../foo"
    assert str(LocalLocation("/tmp/./.")) == "/tmp"

  def test_shouldRaiseExceptionIfPathIsNotAbsolute(self):
    with pytest.raises(LocationInvalidException) as ex:
      LocalLocation("only-relative")
    assert "not absolute" in ex.value.problem

    with pytest.raises(LocationInvalidException):
      LocalLocation("")
