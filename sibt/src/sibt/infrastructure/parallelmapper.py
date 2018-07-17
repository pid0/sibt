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

import threading

class _OccurredException(object):
  def __init__(self, exception):
    self.exception = exception

class _ResultsIterable(object):
  def __init__(self, results):
    self.results = results
    self.i = 0

  def __iter__(self):
    return self

  def __next__(self):
    if self.i >= len(self.results):
      raise StopIteration()

    ret = self.results[self.i]
    self.i += 1

    if isinstance(ret, _OccurredException):
      raise ret.exception
    return ret

class ParallelMapper(object):
  def map(self, mapFunc, xs):
    results = [None for _ in xs]
    threads = [threading.Thread(target=self._threadMain, 
      args=(mapFunc, results, i, x)) for i, x in enumerate(xs)]

    for thread in threads:
      thread.start()
    for thread in threads:
      thread.join()

    return _ResultsIterable(results)

  def _threadMain(self, mapFunc, results, i, x):
    try:
      results[i] = mapFunc(x)
    except Exception as ex:
      results[i] = _OccurredException(ex)
