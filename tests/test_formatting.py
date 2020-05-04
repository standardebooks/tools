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
	"paragraph",
	"poem",
	"song",
	"titlepage",
	"toc",
	"uncopyright",
]

def assert_match(data_dir: Path, test_name: str):
	"""
	Match test input against test output.
	"""

	infile = f"{data_dir}/pretty-print/in/{test_name}.xhtml"
	outfile = f"{data_dir}/pretty-print/out/{test_name}.xhtml"

	with open(infile, "r") as file:
		xml = file.read()

	result = format_xml(xml)
	print(result)

	with open(outfile, "r") as file:
		assert file.read() == result


@pytest.mark.parametrize("test_name", TESTS)
def test_pretty_print(data_dir: Path, test_name: str):
	"""
	Test function for pretty-printing XML with different input files
	"""

	assert_match(data_dir, test_name)
