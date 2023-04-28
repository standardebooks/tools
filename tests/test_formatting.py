"""
Unit tests for formatting functions.
"""

from pathlib import Path

import pytest

from se.formatting import format_xml


TESTS = [
	"colophon",
	"comments",
	"dedication",
	"endnotes",
	"html_header",
	"inline",
	"meta",
	"odps",
	"paragraph",
	"poem",
	"song",
	"titlepage",
	"toc",
	"uncopyright",
	"whitespace",
]

def assert_match(data_dir: Path, test_name: str):
	"""
	Match test input against test output.
	"""

	infile = f"{data_dir}/formatting/in/{test_name}.xhtml"
	outfile = f"{data_dir}/formatting/out/{test_name}.xhtml"

	with open(infile, "r", encoding="utf-8") as file:
		xml = file.read()

	result = format_xml(xml)
	print(result)

	with open(outfile, "r", encoding="utf-8") as file:
		assert file.read() == result


@pytest.mark.parametrize("test_name", TESTS)
def test_format_xml(data_dir: Path, test_name: str):
	"""
	Test function for formatting XML with different input files
	"""

	assert_match(data_dir, test_name)
