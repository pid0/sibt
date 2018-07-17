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

from datetime import timedelta

LocalizedDateTimeFormat = "%c" 
LocalizedTimeOfDayFormat = "%X" 

class DateTimeFormatter(object):
  def __init__(self, clock, useUTC):
    self.clock = clock
    self.useUTC = useUTC

  def _timezoneAdjusted(self, dateTime):
    return dateTime if self.useUTC else dateTime.astimezone()

  def _formatLocalTime(self, localTime):
    date = localTime.date()
    currentDate = self._timezoneAdjusted(self.clock.now()).date()
    difference = date - currentDate

    if abs(difference) > timedelta(days=1):
      return localTime.strftime(LocalizedDateTimeFormat)
    
    timeOfDay = localTime.strftime(LocalizedTimeOfDayFormat)
    day = "Tomorrow" if difference > timedelta() else \
        "Yesterday" if difference < timedelta() else \
        "Today"
    return "{0}, {1}".format(day, timeOfDay)

  def _differenceInHoursAndMins(self, now, dateTime):
    difference = dateTime - now
    timeIsInThePast = difference < timedelta()
    difference = abs(difference)

    if difference > timedelta(hours=9):
      return ""

    hours, remainder = divmod(difference, timedelta(hours=1))
    minutes = round(remainder / timedelta(minutes=1))

    if minutes == 60:
      minutes = 0
      hours = 1

    formatString = "{0}{1}m ago" if timeIsInThePast else "In {0}{1}m" 
    return formatString.format("{0}h".format(hours) if hours > 0 else "", 
        minutes)

  def format(self, dateTime):
    localTime = self._timezoneAdjusted(dateTime)
    if abs(dateTime - self.clock.now()) <= timedelta(seconds=30):
      return "About now"

    hoursAndMinutesLeft = self._differenceInHoursAndMins(
        self.clock.now(), dateTime)
    if hoursAndMinutesLeft != "":
      hoursAndMinutesLeft = " ({0})".format(hoursAndMinutesLeft)

    return self._formatLocalTime(localTime) + hoursAndMinutesLeft
