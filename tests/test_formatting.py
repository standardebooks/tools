"""
Unit tests for formatting functions.
"""

from pathlib import Path

import pytest

from se.formatting import pretty_print_xml


TESTS = [
	"endnotes",
	"colophon",
	"dedication",
	"html_header",
	"inline",
	"nested_blocks",
	"paragraph",
	"poem",
	"song",
	"titlepage",
	"toc",
	"uncopyright",
]

def assert_match(data_dir: Path, test_name: str, single_lines: bool):
	"""
	Match test input against test output.
	"""

	infile = f"{data_dir}/pretty-print/in/{test_name}.xhtml"
	outfile = f"{data_dir}/pretty-print/out/{test_name}.xhtml"

	with open(infile, "r") as file:
		xml = file.read()

	result = pretty_print_xml(xml, single_lines)
	print(result)

	with open(outfile, "r") as file:
		assert file.read() == result


@pytest.mark.parametrize("test_name", TESTS)
def test_pretty_print(data_dir: Path, test_name: str):
	"""
	Test function for pretty-printing XML with different input files
	"""

	assert_match(data_dir, test_name, single_lines=False)


TESTS_SINGLE_LINE = [
	"colophon",
	"dedication",
	"paragraph",
	"poem",
	"song",
]

@pytest.mark.parametrize("test_name", TESTS_SINGLE_LINE)
def test_pretty_print_single_line(data_dir: Path, test_name: str):
	"""
	Test function for pretty-printing XML with single-lines enabled
	"""

	assert_match(data_dir, f"{test_name}-single-line", single_lines=True)
