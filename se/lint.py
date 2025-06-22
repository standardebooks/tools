#!/usr/bin/env python3
"""
Defines classes and helper functions for linting. In particular searching file
text that includes line number references.
"""

from bisect import bisect_right
from pathlib import Path
from typing import List, Optional, Tuple, Union

import regex

XML_COMMENT_PATTERN = regex.compile(r"<!--.+?-->", flags=regex.DOTALL)
NEWLINE_PATTERN = regex.compile(r"\n")

class SourceFile:
	"""
	A source file that can perform regex searches of input text that provides line
	number references to matches.
	"""

	def __init__(self, filename: Path, contents: str, bounds: Optional[List[Tuple[int, int]]] = None):
		self.filename = filename
		self.contents = contents
		self._lines = _ensure_line_bounds(contents, bounds)
		# For binary searching line number lookups on regex matches
		self._offsets = [offset for (offset, _) in self._lines]

	def sub(self, pattern: Union[str, regex.Pattern], replacement: str = "") -> 'SourceFile':
		"""
		Creates a modified view of the source text that retains line number mappings
		to the original text.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		contents, bounds = sub_with_line_mapping(self.contents, pattern, replacement, self._lines)
		return SourceFile(self.filename, contents, bounds)

	def search(self, pattern: Union[str, regex.Pattern]) -> Union[Tuple[str, int], None]:
		"""
		Search the file contents to find the first regex match, with line number.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		match = pattern.search(self.contents)
		if match:
			return (match.group(), self.line_num(match))

		return None

	def findall(self, pattern: Union[str, regex.Pattern]) -> List[Tuple[str, int]]:
		"""
		Find all regex matches in the file contents, including line numbers.
		"""
		if isinstance(pattern, str):
			pattern = regex.compile(pattern)

		matches = []
		for match in regex.finditer(pattern, self.contents):
			matches.append((match.group(), self.line_num(match)))

		return matches

	def line_num(self, match: regex.Match) -> int:
		"""
		Get the original line number based on a regex match of contents.
		"""
		idx = bisect_right(self._offsets, match.start()) - 1
		return 0 if idx < 0 else self._lines[idx][1]

def sub_with_line_mapping(contents: str, pattern: regex.Pattern, replacement: str = "", bounds: Optional[List[Tuple[int, int]]] = None) -> Tuple[str, List[Tuple[int, int]]]:
	"""
	Processes the contents string, replacing matched patterns while building an
	index mapping of byte offsets in the modified output to line numbers of the
	original input string.
	"""
	bounds = _ensure_line_bounds(contents, bounds)

	prev_idx = 0
	removed_chars = 0
	for match in pattern.finditer(contents):
		# Updating offsets between the prior comment and current match
		while prev_idx < len(bounds) and bounds[prev_idx][0] <= match.start():
			entry = bounds[prev_idx]
			bounds[prev_idx] = (entry[0] - removed_chars, entry[1])
			prev_idx += 1

		removed_chars += (match.end() - match.start()) - len(replacement)

		# Delete entries for matches that span multiple lines
		while prev_idx < len(bounds) and bounds[prev_idx][0] < match.end():
			del bounds[prev_idx]

	# Update offsets for lines after the final comment as-needed
	if removed_chars > 0:
		while prev_idx < len(bounds):
			entry = bounds[prev_idx]
			bounds[prev_idx] = (entry[0] - removed_chars, entry[1])
			prev_idx += 1

	return (pattern.sub(replacement, contents), bounds)

def _ensure_line_bounds(contents: str, bounds: Optional[List[Tuple[int, int]]] = None) -> List[Tuple[int, int]]:
	if bounds:
		return list(bounds)

	return [(0,1)] + [
		(match.start() + 1, line)
		for (line, match) in enumerate(NEWLINE_PATTERN.finditer(contents), 2)
	]
