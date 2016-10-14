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
