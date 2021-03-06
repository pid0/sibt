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

from sibt.configuration.exceptions import ConfigSyntaxException, \
    MissingConfigValuesException
import pytest
from test.common.assertutil import iterToTest
from sibt.configuration.cachinginifilelistreader import CachingIniFileListReader

class Fixture(object):
  def __init__(self, tmpdir):
    self.tmpdir = tmpdir
    self.filesDir = tmpdir.mkdir("files1")
    self.files2Dir = tmpdir.mkdir("files2")
    self.useAllowedSections(["a", "b", "c"])

  def useAllowedSections(self, allowedSections):
    self.iniFileReader = CachingIniFileListReader([str(self.filesDir)],
        allowedSections)
    
  def writeFile(self, name, contents):
    path = self.filesDir.join(name)
    path.write(contents)
    return str(path)

  def sectionsOf(self, *paths, instanceArgument=None):
    return self.iniFileReader.sectionsFromFiles(
        [str(self.filesDir.join(path)) for path in paths], instanceArgument)
    
@pytest.fixture
def fixture(tmpdir):
  return Fixture(tmpdir)

def test_shouldReturnDictWithAllowedSectionsAndGlobal(fixture):
  fixture.writeFile("foo", "")

  assert fixture.sectionsOf("foo") == { "a": {}, "b": {}, "c": {}, 
      "Global": {} }

  fixture.useAllowedSections([])
  assert fixture.sectionsOf("foo") == { "Global": {} }
  
def test_shouldParseOptionsAsEntriesInRespectiveSectionsIncludingGlobalEntries(
    fixture):
  fixture.writeFile("some-config", 
      r"""  
      Option2 = %%r
[a]
Group = foo

      [c]
      
Option1=%(Option2)squux
[b]
  
  Option3 = yes""")

  sections = fixture.sectionsOf("some-config")
  assert sections["a"] == {"Group": "foo", "Option2": "%r"}
  assert sections["b"] == {"Option3": "yes", "Option2": "%r"}
  assert sections["c"] == {"Option1": "%rquux", "Option2": "%r"}
  assert sections["Global"] == {"Option2": "%r"}

def test_shouldThrowExceptionIfItEncountersASyntaxError(fixture):
  invalid = fixture.writeFile("invalid", "blah")
  with pytest.raises(ConfigSyntaxException) as ex:
    fixture.sectionsOf("invalid")

  assert ex.value.file == invalid

  fixture.writeFile("invalid", r"""
  [a]
  foo = %(_bar)s
  [b]
  _bar = 1
  """)
  with pytest.raises(MissingConfigValuesException):
    fixture.sectionsOf("invalid")

def test_shouldThrowExceptionIfAnUnknownSectionIsPresent(fixture):
  fixture.writeFile("invalid", """
  [FooSection]
  Lala = 2
  [a]
  [b]
  """)
  with pytest.raises(ConfigSyntaxException) as ex:
    fixture.sectionsOf("invalid")
  assert "FooSection" in str(ex.value)

def test_shouldRemoveOptionsBeginningWithAnUnderscore(fixture):
  fixture.writeFile("using-templates", 
      """[c]
      _Template = bar
      Opt1 = %(_Template)s
        foo
      [b]
      """)

  assert fixture.sectionsOf("using-templates")["c"] == { "Opt1": "bar\nfoo" }

def test_shouldReadImportedB_nWhenReadingRuleAAndMakeAsSettingsOverrideAnyB_is(
    fixture):
  fixture.writeFile("base.inc", """
  [c]
  Loc = /mnt/%(Bar)s
  Base = 3
  Bar = base
  """)
  fixture.writeFile("which-includes-more.inc", "#import base")
  fixture.writeFile("include.inc", """
  [b]
  Foo = f1
  [c]
  Bar = b1""")
  fixture.writeFile("rule", """
  #import which-includes-more
  #import include
  [b]
  Quux = q2
  Foo = f2
  [c]
  Interpolated = %(Base)s""")

  sections = fixture.sectionsOf("rule")
  assert sections["b"] == {"Foo": "f2", "Quux": "q2"}
  assert sections["c"] == {"Bar": "b1", "Base": "3", "Interpolated": "3", 
    "Loc": "/mnt/b1"}

def test_shouldMakeLatterFilesOverrideSettingsOfFormerOnes(fixture):
  fixture.writeFile("first", r"""
  _global = base
  [b]
  [c]
  Foo = 1
  Quux = %(_global)s
  Bar = %(Foo)s""")
  fixture.writeFile("second", r"""
  _global = special
  [c]
  Foo = 2""")

  assert fixture.sectionsOf("first", "second")["c"] == \
      { "Foo": "2", "Bar": "2" , "Quux": "special"}

def test_shouldProvideAccessToTheInstanceArgument(fixture):
  fixture.writeFile("foo", r"""
  [b]
  [c]
  Target = /var/local/vms/%(_instanceName)s.img
  """)

  assert fixture.sectionsOf("foo", instanceArgument="the-value")["c"] == \
      { "Target": "/var/local/vms/the-value.img" }

