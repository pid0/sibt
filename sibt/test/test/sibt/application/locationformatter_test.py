from sibt.application.locationformatter import locToSSHFSArgs
from test.common.builders import sshLocation

class Test_SSHFSArgsFormatFunctionTest(object):
  def test_shouldPutAColonBetweenHostAndPath(self):
    assert locToSSHFSArgs(sshLocation(host="machine", path="/wiki")) == \
        ["machine:/wiki"]

  def test_shouldPrependLoginNameIfGiven(self):
    assert locToSSHFSArgs(sshLocation(host="host", path="b", login="user")) == \
        ["user@host:b"]

  def test_shouldAddAPortsOptionIfAPortIsGiven(self):
    assert locToSSHFSArgs(sshLocation(host="a", path="b", port="7823")) == \
        ["a:b", "-p", "7823"]
