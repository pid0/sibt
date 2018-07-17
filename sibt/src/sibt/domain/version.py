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

from sibt.infrastructure.caseclassequalityhashcode import \
    CaseClassEqualityHashCode
from datetime import timezone

TimeFormat = "%Y-%m-%dT%H:%M:%S"
class Version(CaseClassEqualityHashCode):
  def __init__(self, rule, time):
    if time.tzinfo is None:
      raise Exception("version must have aware datetime")
    self.rule = rule
    self.ruleName = rule.name
    self.time = time

  @property
  def strWithUTCW3C(self):
    return self.ruleName + "," + self.time.astimezone(
        timezone.utc).strftime(TimeFormat)

  @property
  def strWithLocalW3C(self):
    return self.ruleName + "," + self.time.astimezone().strftime(TimeFormat)

  def __repr__(self):
    return "Version{0}".format((self.rule, self.time.strftime(TimeFormat)))

  def __lt__(self, other):
    return self.time < other.time
