from sibt.domain.validatorcollectionvalidator import \
    ValidatorCollectionValidator
from sibt.domain import subvalidators

def constructRulesValidator(additionalValidators=[]):
  return ValidatorCollectionValidator([[ 
      subvalidators.LocExistenceValidator()
    ], [ 
      subvalidators.LocNotEmptyValidator(), 
      subvalidators.NoOverlappingWritesValidator(),
      subvalidators.NoSourceDirOverwriteValidator(),
      subvalidators.AllSharedOptsEqualValidator(),
      subvalidators.SchedulerCheckValidator(),
      subvalidators.SynchronizerCheckValidator()
    ] + additionalValidators])
