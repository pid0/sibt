from sibt.domain.validatorcollectionvalidator import \
    ValidatorCollectionValidator
from test.common import mock

def test_shouldReturnTheErrorsOfTheFirstValidatorThatReturnsSome():
  rules = [object(), object()]
  errors1 = ["first error", "foo"]
  errors2 = ["second error", "bar"]

  sub1 = mock.mock()
  sub1.expectCallsInOrder(mock.call("validate", (rules,),
    ret=errors1))
  sub2 = mock.mock()
  sub2.expectCallsInOrder(mock.call("validate", (rules,),
    ret=errors2))

  validator = ValidatorCollectionValidator([sub2, sub1])
  assert validator.validate(rules) == errors2

