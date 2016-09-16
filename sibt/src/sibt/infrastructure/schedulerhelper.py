def checkOptionOfEachScheduling(schedulings, optionName, checkFunc):
  ret = []
  for scheduling in schedulings:
    if optionName not in scheduling.options:
      continue
    error = checkFunc(optionName, scheduling.options[optionName], 
        scheduling.ruleName)
    if error is not None:
      ret.append(error)
  return ret
