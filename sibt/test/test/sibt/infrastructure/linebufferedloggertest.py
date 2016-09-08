class LineBufferedLoggerTest(object):
  def test_shouldNotBufferBeyondNewlines(self, fixture):
    def test(logger):
      logger.write(b"foo")
      logger.write(b"bar\n quux")
      assert fixture.readLines() == ["foobar"]

      logger.write(b" last\n")
      assert fixture.readLines()[1] == " quux last"
    
    fixture.callWithLoggerAndClose(test)

  def test_shouldFlushBufferAfterClosing(self, fixture):
    fixture.callWithLoggerAndClose(lambda logger: logger.write(b"foo"))
    assert fixture.readLines() == ["foo"]
  
  def test_shouldIgnoreKeywordArgsIfUnknown(self, fixture):
    fixture.callWithLoggerAndClose(lambda logger: logger.write(b"\n",
      tisTheWind="AndNothingMore"))
