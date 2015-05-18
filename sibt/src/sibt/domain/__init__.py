from sibt.domain.validatorcollectionvalidator import \
    ValidatorCollectionValidator
from sibt.domain import subvalidators

def constructRulesValidator():
  return ValidatorCollectionValidator([[ 
      subvalidators.LocExistenceValidator()
    ], [ 
      subvalidators.LocNotEmptyValidator(), 
      subvalidators.NoOverlappingWritesValidator(),
      subvalidators.NoSourceDirOverwriteValidator(),
      subvalidators.SchedulerCheckValidator()
    ]])
