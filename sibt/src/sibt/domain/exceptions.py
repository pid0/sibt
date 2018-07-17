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

class ValidationException(Exception):
  def __init__(self, errors):
    self.errors = errors

  def __str__(self):
    return "errors when validating rules: " + "\n" + "\n".join(self.errors)

class LocationInvalidException(Exception):
  def __init__(self, stringRepresentation, problem):
    self.stringRepresentation = stringRepresentation
    self.problem = problem

  def __str__(self):
    return "location ‘{0}’ {1}".format(self.stringRepresentation, self.problem)

class LocationNotAbsoluteException(LocationInvalidException):
  def __init__(self, stringRepresentation):
    super().__init__(stringRepresentation, "is not absolute")

class UnstablePhaseException(Exception):
  pass

class LockException(Exception):
  pass

class RuleExecutingException(Exception):
  def __init__(self, rule):
    self.rule = rule

  def __str__(self):
    return "Rule ‘{0}’ is currently executing.".format(self.rule.name)

class UnsupportedProtocolException(Exception):
  def __init__(self, ruleName, optionName, protocol, supportedProtocols=[],
      explanation=""):
    self.optionName = optionName
    self.protocol = protocol
    self.supportedProtocols = supportedProtocols
    self.ruleName = ruleName
    self.explanation = explanation

  def __str__(self):
    return ("rule ‘{0}’: {1} can't have {2} protocol{3}{4}").format(
        self.ruleName, self.optionName, self.protocol, 
        (" because " + self.explanation) if self.explanation != "" else "",
        ("; choose from " + ", ".join(self.supportedProtocols)) if \
            self.supportedProtocols != [] else "")
