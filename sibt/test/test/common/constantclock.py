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

from datetime import datetime, timezone

class ConstantClock(object):
  
  def __init__(self, constantTime, timeOfDay):
    self.constantTime = constantTime
    self.timeOfDay = timeOfDay
    
  @classmethod
  def fromUTCNow(cls):
    return ConstantClock(datetime.now(timezone.utc), 
      datetime.now().time())
  
  def putForward(self, delta):
    return ConstantClock(self.constantTime + delta, self.timeOfDay)
  
  def time(self):
    return self.constantTime
  def localTimeOfDay(self):
    return self.timeOfDay