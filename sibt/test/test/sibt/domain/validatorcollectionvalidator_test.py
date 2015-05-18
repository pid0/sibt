from sibt.domain.validatorcollectionvalidator import \
    ValidatorCollectionValidator
from test.common import mock

def test_shouldReturnTheErrorsOfTheFirstValidatorGroupThatReturnsSome():
  rules = [object(), object()]
  errors1 = ["first error", "foo"]
  errors2 = ["second error", "bar"]
  errors3 = ["third error", "quux"]
  sub0, sub1, sub2, sub3 = mock.mock(), mock.mock(), mock.mock(), mock.mock()

  sub0.expectCalls(mock.call("validate", (rules,), ret=[]))
  sub1.expectCalls(mock.call("validate", (rules,), ret=errors1))
  sub2.expectCalls(mock.call("validate", (rules,), ret=errors2))
  sub3.expectCalls(mock.call("validate", (rules,), ret=errors3))

  validator = ValidatorCollectionValidator([
    [sub0], 
    [sub2, sub1],
    [sub3]])
  assert set(validator.validate(rules)) == set(errors2 + errors1)

