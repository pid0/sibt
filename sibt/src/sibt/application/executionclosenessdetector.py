class ExecutionClosenessDetector(object):
  def __init__(self, clock, minimumAllowableDifference):
    self.clock = clock
    self.minimumDifference = minimumAllowableDifference

  def isInUnstablePhase(self, rule):
    if rule.executing:
      return True

    nextExecution = rule.nextExecution
    if nextExecution is None:
      return False

    difference = abs(nextExecution.startTime - self.clock.now())
    return difference < self.minimumDifference
