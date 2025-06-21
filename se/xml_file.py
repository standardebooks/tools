#!/usr/bin/env python3
"""
Defines X[HT]ML classes and helper functions for searching the input text that
include line number references.
"""

from bisect import bisect_right
from pathlib import Path
from typing import List, Tuple, Union

import regex

import se
import se.easy_xml

class XmlSourceFile:
	"""
	An X[HT]ML source file that can perform dom and regex searches of the text.
	For regex-based searches, it removes comments while maintaining line numbers
	of the original text.
	"""

	def __init__(self, filename: Path, dom: se.easy_xml.EasyXmlTree, contents: str):
		self.filename = filename
		self.dom = dom
		self.contents, self._lines = strip_comments_with_line_mapping(contents)
		# For binary searching line number lookups on regex matches
		self._offsets = [offset for (offset, _) in self._lines]

	def search(self, pattern: Union[str, regex.Pattern]) -> Union[Tuple[str, int, int], None]:
		"""
		Search the file contents to find the first match, with line and column number.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		match = pattern.search(self.contents)
		if match:
			return (match.group(), self.line_num(match), 0)

		return None

	def findall(self, pattern: Union[str, regex.Pattern]) -> List[Tuple[str, int, int]]:
		"""
		Find all matches in the file contents, including line and column numbers.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		matches = []
		for match in regex.finditer(pattern, self.contents):
			matches.append((match.group(), self.line_num(match), 0))

		return matches

	def line_num(self, match: regex.Match) -> int:
		"""
		Get the original line number based on a regex match of contents.
		"""
		idx = bisect_right(self._offsets, match.start()) - 1
		return 0 if idx < 0 else self._lines[idx][1]

def strip_comments_with_line_mapping(contents: str) -> Tuple[str, List[Tuple[int, int]]]:
	"""
	Processes the input XML. Removes any <!-- coment --> substrings and builds an
	index mapping of byte offsets in the modified output to line numbers of the
	original input string.
	"""
	newline_pattern = regex.compile(r"\n")
	comment_pattern = regex.compile(r"<!--.+?-->", flags=regex.DOTALL)

	# Start with the raw line number boundaries
	bounds = [(0,1)] + [
		(match.start() + 1, line)
		for (line, match) in enumerate(newline_pattern.finditer(contents), 2)
	]

	prev_idx = 0
	removed_chars = 0
	for match in comment_pattern.finditer(contents):
		# Updating offsets between the prior comment and current match
		while prev_idx < len(bounds) and bounds[prev_idx][0] <= match.start():
			entry = bounds[prev_idx]
			bounds[prev_idx] = (entry[0] - removed_chars, entry[1])
			prev_idx += 1

		removed_chars += (match.end() - match.start())

		# Delete entries for lines that span multiline comments
		while prev_idx < len(bounds) and bounds[prev_idx][0] < match.end():
			del bounds[prev_idx]

	# Update offsets for lines after the final comment as-needed
	if removed_chars > 0:
		while prev_idx < len(bounds):
			entry = bounds[prev_idx]
			bounds[prev_idx] = (entry[0] - removed_chars, entry[1])
			prev_idx += 1

	return (comment_pattern.sub("", contents), bounds)
