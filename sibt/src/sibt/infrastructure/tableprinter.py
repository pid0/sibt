import itertools
from math import ceil
import re
from sibt.infrastructure.displaystring import DisplayString

def _bold(string):
  return "\033[1m{0}\033[0m".format(string)
def _plain(string):
  return string

def _findAlnumNonAlnumBreakPoint(string):
  reversedString = "".join(reversed(string))
  groupMatch = re.search(r"[^a-zA-Z0-9]+", reversedString)
  if groupMatch is None:
    return None
  return len(string) - groupMatch.start()

def _breakText(string, width):
  displayString = DisplayString(string)
  ret = []
  while len(displayString) > width:
    if str(displayString[0]) == " ":
      displayString = displayString[1:]
      continue

    largestPart, _ = displayString.partition(width)
    splitIndex = _findAlnumNonAlnumBreakPoint(str(largestPart))
    if splitIndex is None:
      splitIndex = largestPart.codepointLen

    ret.append(str(displayString[:splitIndex]))
    displayString = displayString[splitIndex:]
  if len(displayString) > 0:
    ret.append(str(displayString))
  return ret

def _fillString(string, noOfColumnsToFill, alignment):
  if noOfColumnsToFill <= 0:
    return string

  if alignment == "left":
    left = 0
    right = noOfColumnsToFill
  else:
    left, oneMoreRight = divmod(noOfColumnsToFill, 2)
    right = left + oneMoreRight
  return (" " * left) + string + (" " * right)

class _Cell(object):
  def __init__(self, content, decoratorFunc, alignment):
    self.content = content or "n/a"
    self.decoratorFunc = decoratorFunc
    self.preferredWidth = len(self.content)
    self.alignment = alignment

  def draw(self, width, useColors):
    lines = _breakText(self.content, width)
    formattedLines = [_fillString(line,
      width - len(DisplayString(line)), self.alignment) for line in lines]
    if useColors:
      formattedLines = [self.decoratorFunc(line) for line in formattedLines]
    return _textElement(formattedLines, width)

  def numberOfLinesRequiredWithWidth(self, width):
    return len(_breakText(self.content, width))

class _Col(object):
  def __init__(self, cells):
    self.cells = cells
    self.longestCellLen = max((cell.preferredWidth for cell in cells), 
        default=0)
    self.preferredWidth = self.longestCellLen

  def numberOfLinesRequiredWithWidth(self, width):
    if width <= 0:
      return 1e9
    return sum(cell.numberOfLinesRequiredWithWidth(width) for cell in 
        self.cells)

def _makeCol(colInfo, rowValues, makeHeader):
  header = [_Cell(colInfo.header, _bold, "center")] if makeHeader else []
  return _Col(header + 
      [_Cell(colInfo.formatCell(value), _plain, "left") for value in rowValues])

_ColSeparator = "   "

class TablePrinter(object):
  def __init__(self, output, useColors, maxWidth):
    self.output = output
    self.useColors = useColors
    self.maxWidth = 1000 if maxWidth == 0 else maxWidth

  def _printRow(self, cols, colWidths, separator, rowIndex):
    rowElement = _emptyElement()
    for i, col in enumerate(cols):
      rowElement = col.cells[rowIndex].draw(colWidths[i],
          self.useColors).beside(rowElement)
      if i != len(cols) - 1:
        rowElement = separator.beside(rowElement)
    rowElement.print(self.output)
  
  def print(self, rowValues, *columnInfos, printHeaders=True):
    cols = [_makeCol(colInfo, rowValues, printHeaders) for colInfo in 
        columnInfos]
    colWidths = self._computeColumnWidths(self.maxWidth, cols, 
        len(_ColSeparator))

    separator = _textElement([_ColSeparator], len(_ColSeparator))
    for i in range(len(cols[0].cells)):
      self._printRow(cols, colWidths, separator, i)

  def _computeColumnWidths(self, maxWidth, cols, separatorLen):
    stepWidth = 5
    originalWidths = [col.preferredWidth for col in cols]
    widths = list(originalWidths)
    totalWidth = sum(widths) + (len(cols) - 1) * separatorLen
    if totalWidth <= maxWidth:
      return widths

    widthToCut = totalWidth - maxWidth

    for _ in range(ceil(widthToCut / stepWidth)):
      costs = [col.numberOfLinesRequiredWithWidth(width - stepWidth) for
          col, width in zip(cols, widths)]
      bestColIndex = min(enumerate(costs), key=lambda x: x[1])[0]
      widths[bestColIndex] -= stepWidth

    if any(width <= 0 for width in widths):
      return originalWidths
    return widths

class _GraphicalElement(object):
  def __init__(self, lines, width):
    self.lines = lines
    self.height = len(lines)
    self.width = width
  
  def heighten(self, newHeight):
    difference = newHeight - self.height
    linesAbove, oneAdditionalBelow = divmod(difference, 2)
    linesBelow = linesAbove + oneAdditionalBelow
    self.lines = \
        [" " * self.width] * linesAbove + \
        self.lines + \
        [" " * self.width] * linesBelow
  
  def beside(self, toTheLeft):
    self.heighten(toTheLeft.height)
    toTheLeft.heighten(self.height)
    return _textElement([leftLine + thisLine for leftLine, thisLine in 
      zip(toTheLeft.lines, self.lines)], self.width + toTheLeft.width)
  
  def print(self, output):
    for line in self.lines:
      output.println(line)

def _textElement(lines, width):
  return _GraphicalElement(lines, width)
def _emptyElement():
  return _GraphicalElement([], 0)
