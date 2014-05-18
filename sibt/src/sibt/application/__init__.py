from sibt.domain.validatorcollectionvalidator import \
    ValidatorCollectionValidator
from sibt.domain import subvalidators

def constructRulesValidator(queuingSchedulers):
  return ValidatorCollectionValidator([
        subvalidators.LocExistenceValidator(),
        subvalidators.LocAbsoluteValidator(),
        subvalidators.LocNotEmptyValidator(),
        subvalidators.NoOverlappingWritesValidator(),
        subvalidators.NoSourceDirOverwriteValidator(),
        subvalidators.SchedulerCheckValidator(queuingSchedulers)
    ])
