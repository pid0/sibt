from datetime import time, datetime
from sibt import executiontimeprediction

class ConfigPrinter(object):
  def printConfig(self, configuration, output, runPredictor):
    output.println("global.conf:")
    if configuration.timeOfDayRestriction is None:
      output.println("  No time of day restriction")
    else:
      output.println("  Won't run any rules from {0} to {1}".format(
        self._formatTime(configuration.timeOfDayRestriction.start),
        self._formatTime(configuration.timeOfDayRestriction.end)))
    output.println("")
    
    for rule in configuration.rules:
      output.println(rule.title + ":")
      output.println("  Using " + rule.backupProgram)
      output.println("  to backup from \"" + rule.source + "\"")
      output.println('  to "' + rule.destination + '"')
      output.println("  Rule is run every " + 
        self._formatInterval(rule.interval))
      output.println("  Last time run: " + self._formatExecutionTime(
        runPredictor.lastExecutionTimeOf(rule)))
      output.println("  Next time (at the earliest): " + 
        self._formatExecutionTime(runPredictor.predictNextExecutionTimeOf(
          rule, configuration.timeOfDayRestriction)))
      output.println("")
      
  def _formatInterval(self, interval):
    if interval is None:
      return "time"
    if interval.days % 7 == 0:
      return str(interval.days // 7) + " weeks"
    else:
      return str(interval.days) + " days"
    
  def _formatExecutionTime(self, pointInTime):
    return ("n/a" if pointInTime is None else
      "Due" if pointInTime is executiontimeprediction.Due else
      datetime.strftime(pointInTime, "%Y-%m-%d %H:%M:%S.%f %z"))
    
  def _formatTime(self, pointInTime):
    return time.strftime(pointInTime, "%H:%M")