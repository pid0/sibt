from sibt.infrastructure.optioninfoparser import OptionInfoParser

class OptionInfoParsingScheduler(object):
  def __init__(self, protoScheduler):
    self.protoScheduler = protoScheduler

  @property
  def availableOptions(self):
    parser = OptionInfoParser()
    return [parser.parse(optionString) for optionString in 
        self.protoScheduler.availableOptions]

  def __getattr__(self, name):
    return getattr(self.protoScheduler, name)
