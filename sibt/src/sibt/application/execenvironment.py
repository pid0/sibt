# This file is part of sibt (simple backup tool), a program that integrates existing backup tools.
# Copyright 2018 Patrick Plagwitz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from sibt.application.prefixingerrorlogger import PrefixingErrorLogger
from sibt.infrastructure.fileobjoutput import FileObjOutput

class ExecEnvironment(object):
  def __init__(self, syncCall, logger, logSubProcessWith):
    self._syncCall = syncCall
    self._logSubProcessWith = logSubProcessWith
    self.binaryLogger = logger
    self.logger = PrefixingErrorLogger(FileObjOutput(self.binaryLogger),
        "scheduler", 0)

  def runSynchronizer(self):
    return self._logSubProcessWith(self.binaryLogger, self._syncCall) == 0
  
  def logSubProcess(self, *args, **kwargs):
    return self._logSubProcessWith(self.binaryLogger, *args, **kwargs)

  def withLoggerReplaced(self, newBinaryLogger):
    return ExecEnvironment(self._syncCall, newBinaryLogger, 
        self._logSubProcessWith)
