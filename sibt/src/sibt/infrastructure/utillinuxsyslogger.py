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

import subprocess
import shlex
import os
from sibt.infrastructure.exceptions import ExternalFailureException
from sibt.infrastructure.linebufferedlogger import LineBufferedLogger

class UtilLinuxSysLogger(LineBufferedLogger):
  def __init__(self, loggerOptions, prefix=None, 
      facility="user", severity="info", tag=None):
    super().__init__()

    self.prefix = b""
    if prefix is not None:
      self.prefix = prefix + b": "

    self.loggerOptions = loggerOptions
    
    self.facility = facility
    self.severity = severity
    self.tag = tag

  def writeLine(self, line, facility=None, severity=None, **kwargs):
    facility = facility or self.facility
    severity = severity or self.severity

    priority = "{0}.{1}".format(facility, severity)

    execArgs = ["logger"] + shlex.split(self.loggerOptions) + \
        ["--id={0}".format(os.getpid()), "--priority", priority] + \
        (["--tag", self.tag] if self.tag is not None else [])

    with subprocess.Popen(execArgs, stdin=subprocess.PIPE) as loggerProcess:
      loggerProcess.stdin.write(self.prefix + line)

    if loggerProcess.returncode != 0:
      raise ExternalFailureException(execArgs[0], execArgs[1:], 
          loggerProcess.returncode)
