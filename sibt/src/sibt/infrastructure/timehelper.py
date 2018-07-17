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
import time

def toUTC(localDateTime):
  timeTuple = localDateTime.timetuple()
  return datetime.fromtimestamp(time.mktime(timeTuple), timezone.utc)

def withoutTimeOfDay(dateTime):
  return datetime(dateTime.year, dateTime.month, dateTime.day, 0, 0, 0, 0, 
      dateTime.tzinfo)