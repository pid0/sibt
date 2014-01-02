import os.path
from datetime import datetime

class ExecutionTimeFileRepo(object):
  def __init__(self, dirName):
    self.dirName = dirName
    
  def setExecutionTimeFor(self, rule, executionTime):
    with open(os.path.join(self.dirName, rule.title), 'w') as file:
        file.write(self._formatDatetime(executionTime))
        
  def executionTimeOf(self, rule):
    fileName = os.path.join(self.dirName, rule.title)
    if not os.path.exists(fileName):
      return None
    
    with open(fileName, 'r') as file:
      return self._parseDateTime(file.read())
        
  DateFormat = "%Y-%m-%d %H:%M:%S.%f %z"    
  def _formatDatetime(self, time):
    return time.strftime(ExecutionTimeFileRepo.DateFormat)
  def _parseDateTime(self, string):
    return datetime.strptime(string, ExecutionTimeFileRepo.DateFormat)