import pytest
from sibt.application.mountpointassertionstruevalidator import \
    MountPointAssertionsTrueValidator
from test.common.validatortest import fix, ValidatorTest
from test.common.builders import mockRule, ruleSet
from test.common.assertutil import iterToTest, stringThat
from test.common.fusefs import nonEmptyFSMountedAt, fuseIsAvailable

class Test_MountPointAssertionsTrueValidatorTest(ValidatorTest):
  def construct(self):
    return MountPointAssertionsTrueValidator()
  
  @pytest.mark.skipif(not fuseIsAvailable(), reason="Requires FUSE")
  def test_shouldPrintTheActualMountPointIfTheAssertionTurnsOutFalse(self, fix):
    mountPoint = fix.tmpdir.mkdir("mount")

    with nonEmptyFSMountedAt(mountPoint):
      loc1 = mountPoint.mkdir("sub").mkdir("loc1")
      rule = mockRule(loc1=str(loc1), options=dict(MustBeMountPoint="1"))
      errors = self.construct().validate(ruleSet(rule))

    iterToTest(errors).shouldContainMatching(
        stringThat.shouldInclude("actual", str(mountPoint) + "’"))
