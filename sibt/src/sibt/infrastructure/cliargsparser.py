class OptArg(object):
  def __init__(self, name, *aliases, noOfArgs="0"):
    self.name = name
    self.aliases = list(aliases)
    self.noOfArgs = noOfArgs
    self.positional = False

  def toPosArg(self):
    ret = PosArg(self.name, self.noOfArgs)
    ret._allowInterruption = True
    return ret

  def __repr__(self):
    return "OptArg{0}".format((self.name, self.noOfArgs))

class SubGroups(object):
  def __init__(self, *groups, default=None):
    self.groups = list(groups)
    self.default = None if default is None else \
        next(group for group in groups if group.name == default)

  def choiceArg(self, level):
    return PosArg("command" + (str(level + 1) if level > 0 else ""))

  def choose(self, parsedArg):
    for group in self.groups:
      for name in group.aliases + [group.name]:
        if name.startswith(parsedArg.value):
          return group

  def groupWithOpt(self, nameOfOpt):
    for group in self.groups:
      for opt in group.opts:
        if nameOfOpt in [opt.name] + opt.aliases:
          return group

  def __repr__(self):
    return "SubGroups{0}".format((self.groups,))

class SubGroup(object):
  def __init__(self, name, *options):
    if isinstance(name, tuple):
      self.name = name[0]
      self.aliases = list(name[1:])
    else:
      self.name = name
      self.aliases = []

    options = list(options)
    self._optionsArg = options

    groupsObjects = [opt for opt in options if hasattr(opt, "groups")]
    self.groups = groupsObjects[0] if len(groupsObjects) > 0 else None
    options = [opt for opt in options if not hasattr(opt, "groups")]

    self.posOpts = [opt for opt in options if opt.positional]

    self.opts = [opt for opt in options if not opt.positional]
    self.namesToOpts = dict()
    for opt in self.opts:
      for name in [opt.name] + opt.aliases:
        self.namesToOpts[name] = opt

  def _setDefaults(self, resultOpts):
    ret = resultOpts
    for opt in self.opts:
      if opt.noOfArgs == "0":
        ret = _optAdded(ret, opt.name, [], False)
    return ret

  def __repr__(self):
    return "SubGroup{0}".format((self.name, self._optionsArg))

class PosArg(object):
  def __init__(self, name, noOfArgs="1"):
    self.name = name
    self.noOfArgs = noOfArgs
    self.positional = True
    self._allowInterruption = False

  def __repr__(self):
    return "PosArg{0}".format((self.name, self.noOfArgs))

class ParseResult(object):
  def __init__(self, options):
    self.options = options
    self.values = dict((name, opt.value) for name, opt in options.items())

class ParsedOption(object):
  def __init__(self, name, source, value):
    self.name = name
    self.source = source
    self.value = value

  def withSource(self, newSource):
    return ParsedOption(self.name, newSource, self.value)
  def withValue(self, newValue):
    return ParsedOption(self.name, self.source, newValue)

  @property
  def wasActuallyParsed(self):
    return len(self.source) > 0

  def __repr__(self):
    return "ParsedOption{0}".format((self.name, self.source, self.value))

def _optsMerged(resultOpts, *opts, checkDuplicates=False):
  ret = resultOpts
  for opt in opts:
    if checkDuplicates and opt.name in ret and ret[opt.name].wasActuallyParsed:
      raise OptionalUsedTwiceException("--" + opt.name)
    ret[opt.name] = opt
  return ret

def _optAdded(resultOpts, name, *args):
  resultOpts[name] = ParsedOption(name, *args)
  return resultOpts

def _formatPosArg(arg):
  ret = "<{0}>".format(arg.name + ("..." if arg.noOfArgs in ["*", "+"] else ""))
  return "[" + ret + "]" if arg.noOfArgs == "*" else ret

def _formatOptArg(arg):
  ret = "[--{0}".format(arg.name)
  if arg.noOfArgs != "0":
    ret += " <arg{0}>".format("..." if arg.noOfArgs == "*" else "")
  return ret + "]"

def _buildGrammarString(posOpts, opts=[]):
  optArgsStrings = [_formatOptArg(opt) for opt in opts]
  posArgsStrings = [_formatPosArg(opt) for opt in posOpts]
  return " ".join(optArgsStrings + posArgsStrings)

class ParseState(object):
  def __init__(self, remainingArgs, positionals, namesToOpts, acceptOpts):
    self.args = remainingArgs
    self.posOpts = positionals
    self.acceptOpts = acceptOpts
    self.namesToOpts = namesToOpts

  def argsPrepended(self, *newArgs):
    return ParseState(list(newArgs) + self.args, self.posOpts, 
        self.namesToOpts, self.acceptOpts)
  def argPopped(self):
    return ParseState(self.args[1:], self.posOpts, self.namesToOpts, 
        self.acceptOpts)
  def posOptsPrepended(self, *newPositionals):
    return ParseState(self.args, list(newPositionals) + self.posOpts, 
        self.namesToOpts, self.acceptOpts)
  def posOptPopped(self):
    return ParseState(self.args, self.posOpts[1:], self.namesToOpts, 
        self.acceptOpts)
  def acceptingOpts(self, acceptOpts):
    return ParseState(self.args, self.posOpts, self.namesToOpts, acceptOpts)

  def withNewPosOpts(self, newPositionals):
    return ParseState(self.args, newPositionals, self.namesToOpts,
        self.acceptOpts)
  def optsMerged(self, newNamesToOpts):
    namesToOpts = dict(self.namesToOpts)
    for name, opt in newNamesToOpts.items():
      assert name not in namesToOpts
      namesToOpts[name] = opt
    return ParseState(self.args, self.posOpts, namesToOpts, self.acceptOpts)
  
class CliParser(object):
  def __init__(self, options):
    self.rootGroups = SubGroups(SubGroup("group", *options))

  def grammarString(self, groupsTrail=[], progName=None, 
      fullDescriptions=False):
    groupsTrail = [self.rootGroups.groups[0]] + groupsTrail

    stringParts = [progName or ""]

    for i, previousGroup in enumerate(groupsTrail):
      if i > 0:
        stringParts.append(previousGroup.name)
      stringParts.append(_buildGrammarString([], previousGroup.opts))

    group = groupsTrail[-1]
    posOpts = [group.groups.choiceArg(len(groupsTrail) - 1)] if \
        group.groups is not None else group.posOpts

    stringParts.append(_buildGrammarString(posOpts))
    if fullDescriptions:
      descriptions = self._optDescriptions(group)
      if len(descriptions) > 0:
        stringParts.append("\n\n" + descriptions)

    return " ".join(part for part in stringParts if len(part) > 0)

  def _optDescriptions(self, group):
    if group.groups is not None:
      return "command can be\n" + "\n".join("  " + group.name for group in \
          group.groups.groups)
    return ""

  def helpString(self, groupsTrail=[], **kwargs):
    return self.grammarString(groupsTrail, fullDescriptions=True, **kwargs)

  def parseArgs(self, args):
    parseState = ParseState(list(args), [], {}, True)

    resultOpts, _ = self._parseGroups(parseState, self.rootGroups, -1)

    return ParseResult(resultOpts)

  def _chooseGroup(self, state, groupsObj, groupLevel):
    result = {}
    if len(groupsObj.groups) == 1:
      newGroup = groupsObj.groups[0]
    else:
      choiceArg = groupsObj.choiceArg(groupLevel)
      try:
        result, state = self._parseUntil(choiceArg, state)
        newGroup = groupsObj.choose(result[choiceArg.name])
        if newGroup is None:
          newGroup = groupsObj.default
          state = state.argsPrepended(*result[choiceArg.name].source)
      except (TooFewArgsException, UnknownOptionalException) as ex:
        newGroup = groupsObj.default if isinstance(ex, TooFewArgsException) \
            else groupsObj.groupWithOpt(ex.nameOfOpt)
        if newGroup is None:
          raise
      result = _optAdded(result, choiceArg.name, [newGroup.name], newGroup.name)

    return newGroup, result, state

  def _parseGroups(self, state, groupsObj, groupLevel):
    newGroup, result, state = self._chooseGroup(state, groupsObj, groupLevel)
    try:
      initializedResult = newGroup._setDefaults(result)
      state = state.withNewPosOpts(newGroup.posOpts).optsMerged(
          newGroup.namesToOpts)

      if newGroup.groups is not None:
        result, state = self._parseGroups(state, newGroup.groups, 
            groupLevel + 1)
      else:
        result, state = self._parseAll(state)

      return _optsMerged(initializedResult, *result.values()), state
    except ParseException as ex:
      if groupLevel >= 0:
        ex.groupsTrail = [newGroup] + ex.groupsTrail
      raise

  def _isOptional(self, arg):
    return arg.startswith("-") and len(arg) > 1

  def _parseAll(self, state):
    result = {1: 2}
    ret = dict()
    while len(result) != 0:
      result, state = self._parseOne(state)
      ret = _optsMerged(ret, *result.values(), checkDuplicates=True)

    if len(state.args) > 0:
      raise TooManyArgsException(state.args)

    return ret, state

  def _parseOne(self, state, firstMayBeOptional=True):
    if len(state.args) > 0 and state.args[0] == "--":
      return {}, state.acceptingOpts(False).argPopped()
    if len(state.args) > 0 and self._isOptional(state.args[0]) and \
        state.acceptOpts:
      if not firstMayBeOptional:
        raise _UnexpectedOptionalAsFirstArgException(_buildGrammarString(
          state.posOpts))
      return self._parseOptional(state.args[0], state.argPopped())
    if len(state.posOpts) == 0 and len(state.args) == 0:
      return {}, state
    if len(state.args) == 0 and not state.posOpts[0].noOfArgs == "*":
      raise TooFewArgsException(_buildGrammarString(state.posOpts))
    if len(state.posOpts) == 0:
      return {}, state

    nextPositional = state.posOpts[0]
    if nextPositional.noOfArgs in ["*", "+"]:
      return self._parseStar(state.posOpts[0], state.posOptPopped())
    else:
      return _optAdded({}, nextPositional.name, [state.args[0]], 
        state.args[0]), state.argPopped().posOptPopped()

  def _parseStar(self, positional, state):
    resultOpts = {}
    parsedArgs = []
    while len(state.args) > 0:
      if self._isOptional(state.args[0]) and state.acceptOpts:
        if positional._allowInterruption and state.args[0] != "--":
          break
        result, state = self._parseOne(state)
        resultOpts = _optsMerged(resultOpts, *result.values())
        continue
      parsedArgs.append(state.args[0])
      state = state.argPopped()

    return _optAdded(resultOpts, positional.name, parsedArgs, 
        parsedArgs), state

  def _findOptional(self, name, state):
    ret = state.namesToOpts.get(name, None)
    if ret is None:
      raise UnknownOptionalException(name)
    return ret

  def _splitShortOptArg(self, state, strippedArg, _):
    opt = self._findOptional(strippedArg[0], state)
    canonicalArg = "--" + opt.name
    if opt.noOfArgs != "0":
      return [strippedArg[1:]], opt, canonicalArg
    if len(strippedArg) > 1:
      return ["-" + strippedArg[1:]], opt, canonicalArg
    return [], opt, canonicalArg

  def _splitLongOptArg(self, state, strippedArg, arg):
    indexOfEqualsSign = strippedArg.find("=")
    if indexOfEqualsSign != -1 and arg.startswith("--"):
      name = strippedArg[0:indexOfEqualsSign]
      value = strippedArg[indexOfEqualsSign+1:]
      opt = self._findOptional(name, state)
      if opt.noOfArgs == "0":
        raise UnexpectedOptionalValueException(name, value)
      return [value], self._findOptional(name, state), "--" + name

    return [], self._findOptional(strippedArg, state), arg

  def _parseOptional(self, nameArg, state):
    strippedArg = nameArg[1:] if nameArg[1] != "-" else nameArg[2:]

    splitFunc = self._splitShortOptArg if nameArg[1] != "-" else \
        self._splitLongOptArg

    newArgs, opt, canonicalArg = splitFunc(state, strippedArg, nameArg)
    state = state.argsPrepended(*newArgs)

    if opt.noOfArgs == "0":
      return _optAdded({}, opt.name, [canonicalArg], True), state 
    else:
      try:
        result, state = self._parseUntil(opt.toPosArg(), state,
            firstMayBeOptional=False)
        return  _optsMerged(result, result[opt.name].withSource(
          [canonicalArg] + result[opt.name].source)), state
      except (TooFewArgsException, _UnexpectedOptionalAsFirstArgException) \
          as ex:
        raise MissingOptionalArgsException(ex.remainingGrammar, canonicalArg)

  def _parseUntil(self, positional, state, firstMayBeOptional=True):
    resultOpts = {}
    state = state.posOptsPrepended(positional)
    while positional.name not in resultOpts:
      result, state = self._parseOne(state, 
          firstMayBeOptional=firstMayBeOptional)
      resultOpts = _optsMerged(resultOpts, *result.values())
    return resultOpts, state

class ParseException(Exception):
  def __init__(self): 
    self.groupsTrail = []

class TooManyArgsException(ParseException):
  def __init__(self, remainingArgs):
    super().__init__()
    self.remainingArgs = remainingArgs

  def __str__(self):
    return "too many arguments: remaining: {0}".format(
        ", ".join(self.remainingArgs))

class TooFewArgsException(ParseException):
  def __init__(self, remainingGrammar):
    super().__init__()
    self.remainingGrammar = remainingGrammar

  def __str__(self):
    return "too few arguments; missing: {0}".format(self.remainingGrammar)

class MissingOptionalArgsException(TooFewArgsException):
  def __init__(self, remainingGrammar, optName):
    super().__init__(remainingGrammar)
    self.optName = optName

  def __str__(self):
    return "{0} option lacks arguments, needed: {1}".format(self.optName,
        self.remainingGrammar)

class UnknownOptionalException(ParseException):
  def __init__(self, nameOfOpt):
    super().__init__()
    self.nameOfOpt = nameOfOpt
    self.printableName = ("-" if len(nameOfOpt) == 1 else "--") + nameOfOpt

  def __str__(self):
    return "unknown option {0}".format(self.printableName)

class _UnexpectedOptionalAsFirstArgException(ParseException):
  def __init__(self, remainingGrammar):
    super().__init__()
    self.remainingGrammar = remainingGrammar

class OptionalUsedTwiceException(ParseException):
  def __init__(self, optName):
    super().__init__()
    self.optName = optName

  def __str__(self):
    return "option {0} used twice".format(self.optName)

class UnexpectedOptionalValueException(ParseException):
  def __init__(self, optName, value):
    super().__init__()
    self.optName = optName
    self.value = value

  def __str__(self):
    return "option {0} doesn't take a value ({1} given)".format(self.optName,
        self.value)

def standardParse(parser, progName, args, stdout, stderr):
  prefix = "Usage: " + progName
  try:
    try:
      return None, parser.parseArgs(args)
    except UnknownOptionalException as ex:
      if ex.nameOfOpt == "help":
        stdout.println(parser.helpString(ex.groupsTrail, progName=prefix))
        return 0, None
      raise
  except ParseException as ex:
    stderr.println(str(ex))
    stderr.println(parser.helpString(ex.groupsTrail, progName=prefix))
    return 2, None
