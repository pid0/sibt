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

import os
import struct
from datetime import datetime, timedelta, timezone
import traceback

from sibt.domain.execution import Execution, ExecutionResult
from sibt.infrastructure.linebufferedlogger import LineBufferedLogger
from sibt.infrastructure.fcntlmutexmanager import tryToLock, readLock, writeLock

TimeFormat = "%Y-%m-%dT%H:%M:%S.%f%z"
Encoding = "utf-8"
SeekSet = 0
SeekCur = 1
SeekEnd = 2
BigEndian32BitUInt = ">I"
UnsetLength = b"\xFF\xFF\xFF\xFF"
LargerThanHeaderOrFooter = 2**12

class _LogFileLogger(LineBufferedLogger):
  def __init__(self, file):
    super().__init__()
    self.file = file

  def writeLine(self, line, **kwargs):
    self.file.write(line)
    self.file.flush()

def _encode(string):
  return string.encode(Encoding)
def _decode(bytesObject):
  return bytesObject.decode(Encoding)

def _callCatchingExceptions(logFile, execute, succeeded):
  try:
    succeeded[0] = execute(logFile)
  except BaseException as ex:
    logFile.write(b"internal exception (caught in log):\n")
    if isinstance(ex, Exception):
      logFile.write(_encode(traceback.format_exc()))
    else:
      logFile.write(_encode(str(ex)))
    succeeded[0] = False
    raise

class FilesDBExecutionsLog(object):
  def __init__(self, logDir, ruleNamePrefix=""):
    self.logDir = logDir
    self.ruleNamePrefix = ruleNamePrefix
    self._lockedPaths = set()
    self._filesToClose = []

  def _closeFiles(self):
    for fileToClose in self._filesToClose:
      fileToClose.close()
    self._filesToClose.clear()

  def _lock(self, file, filePath):
    writeLock(file)
    self._lockedPaths.add(filePath)

  def _isLocked(self, filePath):
    if filePath in self._lockedPaths:
      return True
    with open(filePath, "r") as file:
      couldLock = tryToLock(file, readLock)
    return not couldLock

  def executionsOfRules(self, ruleNames):
    return dict((ruleName, self._executionsOfRule(
      self._storageName(ruleName))) for ruleName in ruleNames)

  def _executionsOfRule(self, ruleName):
    folderPath, loggingFileNames = self._readLogFolder(ruleName, create=False)
    return [self._readLoggingFile(os.path.join(folderPath, fileName)) for 
        fileName in loggingFileNames]

  def _readLoggingFile(self, filePath):
    file = open(filePath, "rb", buffering=LargerThanHeaderOrFooter)
    try:
      return self._parseLoggingFile(file, filePath)
    finally:
      if filePath in self._lockedPaths:
        self._filesToClose.append(file)
      else:
        file.close()

  def _parseLoggingFile(self, file, filePath):
    startTime = datetime.strptime(_decode(file.readline()[:-1]), TimeFormat)
    lengthField = file.read(4)

    if lengthField == UnsetLength:
      output = self._readTextUntilEnd(file)
      result = None
      if not self._isLocked(filePath):
        output += "\nError: Log entry could not be finished (crashed?)"
        result = ExecutionResult(startTime + timedelta(hours=2), False)
    else:
      output = self._readTextOfLength(file, lengthField)
      endTime = datetime.strptime(_decode(file.readline()[:-1]), TimeFormat)
      succeeded = file.readline()[:-1] == b"True"

      result = ExecutionResult(endTime, succeeded)

    return Execution(startTime, output, result)

  def _readTextUntilEnd(self, file):
    currentPosition = file.tell()
    outputLength = file.seek(0, SeekEnd) - currentPosition
    file.seek(currentPosition, SeekSet)
    return _decode(file.read(outputLength))

  def _readTextOfLength(self, file, lengthBytes):
    outputLength = struct.unpack(BigEndian32BitUInt, lengthBytes)[0]
    ret = _decode(file.read(outputLength))
    file.readline()
    return ret


  def logExecution(self, ruleName, clock, writeSchedulingOutput):
    folderPath, loggingFileNames = self._readLogFolder(
        self._storageName(ruleName), create=True)
    latestLoggingNumber = 0 if len(loggingFileNames) == 0 else \
        int(loggingFileNames[-1])

    self._writeLoggingFile(
        os.path.join(folderPath, str(latestLoggingNumber + 1)), 
        clock, writeSchedulingOutput)

  def _writeLoggingFile(self, filePath, clock, writeExecutionOutput):
    with open(filePath, "wb") as file:
      self._lock(file, filePath)
      textLengthFieldPos = self._writeHeader(file, clock.now())
      file.flush()

      executionSucceeded = [None]
      logger = _LogFileLogger(file)
      try:
        _callCatchingExceptions(logger, writeExecutionOutput, 
            executionSucceeded)
      finally:
        logger.close()
        textLength = file.tell() - textLengthFieldPos - 4

        file.seek(textLengthFieldPos, SeekSet)
        file.write(struct.pack(BigEndian32BitUInt, textLength))
        file.seek(0, SeekEnd)

        self._writeFooter(file, clock.now(), executionSucceeded[0] is True)
        self._closeFiles()
        self._lockedPaths.remove(filePath)

  def _writeHeader(self, file, startTime):
    file.write(_encode(startTime.strftime(TimeFormat)))
    file.write(b"\n")

    textLengthFieldPos = file.tell()
    file.write(UnsetLength)
    return textLengthFieldPos

  def _writeFooter(self, file, endTime, succeeded):
    file.write(b"\n")
    file.write(_encode(endTime.strftime(TimeFormat)))
    file.write(b"\n")
    file.write(b"True" if succeeded else b"False")
    file.write(b"\n")

  def _readLogFolder(self, ruleName, create):
    folderPath = os.path.join(self.logDir, ruleName)

    if not os.path.isdir(folderPath):
      if not create:
        return folderPath, []
      os.mkdir(folderPath)

    loggingFileNames = sorted(os.listdir(folderPath),
        key=lambda fileName: int(fileName))
    return folderPath, loggingFileNames

  def _storageName(self, ruleName):
    return ruleName[len(self.ruleNamePrefix):]
