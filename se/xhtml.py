#!/usr/bin/env python3
"""
Defines various XHTML classes and helper functions.
"""

from pathlib import Path
from typing import List, Tuple, Union

import regex

import se
import se.easy_xml

class XhtmlSourceFile:
	"""
	An XHTML source file that caches the filename, dom, contents and lines.
	"""

	def __init__(self, filename: Path, dom: se.easy_xml.EasyXmlTree, contents: str):
		self.filename = filename
		self.dom = dom
		self.contents = contents
		self.lines = contents.splitlines()

	def search(self, pattern: Union[str, regex.Pattern]) -> Union[Tuple[str, int, int], None]:
		"""
		Search the file contents to find the first match, with line and column number.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		for line_num, line in enumerate(self.lines, 1):
			match = pattern.search(line)
			if match:
				return (match.group(), line_num, match.start()+1)

		return None

	def findall(self, pattern: Union[str, regex.Pattern]) -> List[Tuple[str, int, int]]:
		"""
		Find all matches in the file contents, including line and column numbers.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		matches = []
		for line_num, line in enumerate(self.lines, 1):
			for match in regex.finditer(pattern, line):
				matches.append((match.group(), line_num, match.start()+1))

		return matches
