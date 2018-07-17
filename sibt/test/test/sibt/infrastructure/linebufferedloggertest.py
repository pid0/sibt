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
