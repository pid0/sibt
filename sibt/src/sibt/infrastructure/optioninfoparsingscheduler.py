from sibt.infrastructure.optioninfoparser import OptionInfoParser

def _optInfosFromStrings(strings):
  parser = OptionInfoParser()
  return [parser.parse(optionString) for optionString in strings]

class OptionInfoParsingScheduler(object):
  def __init__(self, protoScheduler):
    self.protoScheduler = protoScheduler

    self._individualOpts = _optInfosFromStrings(
        self.protoScheduler.availableOptions)
    self.availableSharedOptions = _optInfosFromStrings(
        self.protoScheduler.availableSharedOptions)
    self.availableOptions = self._individualOpts + self.availableSharedOptions

  def __getattr__(self, name):
    return getattr(self.protoScheduler, name)
