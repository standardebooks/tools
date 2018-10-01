#!/usr/bin/env python3

import sys
import os
from typing import Union
from textwrap import wrap
from termcolor import colored
import terminaltables
import regex


MESSAGE_INDENT = "    "
UNICODE_BOM = "\ufeff"
NO_BREAK_SPACE = "\u00a0"
WORD_JOINER = "\u2060"
HAIR_SPACE = "\u200a"
ZERO_WIDTH_SPACE = "\ufeff"
SHY_HYPHEN = "\u00ad"
IGNORED_FILENAMES = ["colophon.xhtml", "titlepage.xhtml", "imprint.xhtml", "uncopyright.xhtml", "halftitle.xhtml", "toc.xhtml", "loi.xhtml"]
XHTML_NAMESPACES = {"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops", "z3998": "http://www.daisy.org/z3998/2012/vocab/structure/", "se": "https://standardebooks.org/vocab/1.0", "dc": "http://purl.org/dc/elements/1.1/", "opf": "http://www.idpf.org/2007/opf"}
FRONTMATTER_FILENAMES = ["dedication.xhtml", "introduction.xhtml", "preface.xhtml", "prologue.xhtml", "foreword.xhtml", "preamble.xhtml", "titlepage.xhtml", "halftitlepage.xhtml", "imprint.xhtml"]
BACKMATTER_FILENAMES = ["endnotes.xhtml", "loi.xhtml", "epilogue.xhtml", "afterword.xhtml", "appendix.xhtml", "colophon.xhtml", "uncopyright.xhtml"]
BINARY_EXTENSIONS = [".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".png", ".epub", ".epub3", ".xcf"]
SE_GENRES = ["Adventure", "Autobiography", "Biography", "Childrens", "Comedy", "Drama", "Fantasy", "Fiction", "Horror", "Memoir", "Mystery", "Nonfiction", "Philosophy", "Poetry", "Romance", "Satire", "Science Fiction", "Shorts", "Spirituality", "Tragedy", "Travel"]
ARIA_ROLES = ["afterword", "appendix", "biblioentry", "bibliography", "chapter", "colophon", "conclusion", "dedication", "epigraph", "epilogue", "foreword", "introduction", "noteref", "part", "preface", "prologue", "subtitle", "toc"]
MESSAGE_TYPE_WARNING = 1
MESSAGE_TYPE_ERROR = 2
COVER_TITLE_BOX_Y = 1620 # In px; note that in SVG, Y starts from the TOP of the image
COVER_TITLE_BOX_HEIGHT = 430
COVER_TITLE_BOX_WIDTH = 1300
COVER_TITLE_BOX_PADDING = 100
COVER_TITLE_MARGIN = 20
COVER_TITLE_HEIGHT = 80
COVER_TITLE_SMALL_HEIGHT = 60
COVER_TITLE_XSMALL_HEIGHT = 50
COVER_AUTHOR_SPACING = 60
COVER_AUTHOR_HEIGHT = 40
COVER_AUTHOR_MARGIN = 20
TITLEPAGE_WIDTH = 1400
TITLEPAGE_VERTICAL_PADDING = 50
TITLEPAGE_HORIZONTAL_PADDING = 100
TITLEPAGE_TITLE_HEIGHT = 80 # Height of each title line
TITLEPAGE_TITLE_MARGIN = 20 # Space between consecutive title lines
TITLEPAGE_AUTHOR_SPACING = 100 # Space between last title line and first author line
TITLEPAGE_AUTHOR_HEIGHT = 60 # Height of each author line
TITLEPAGE_AUTHOR_MARGIN = 20 # Space between consecutive author lines
TITLEPAGE_CONTRIBUTORS_SPACING = 150 # Space between last author line and first contributor descriptor
TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_HEIGHT = 40 # Height of each contributor descriptor line
TITLEPAGE_CONTRIBUTOR_HEIGHT = 40 # Height of each contributor line
TITLEPAGE_CONTRIBUTOR_MARGIN = 20 # Space between contributor descriptor and contributor line, and between sequential contributor lines
TITLEPAGE_CONTRIBUTOR_DESCRIPTOR_MARGIN = 80 # Space between last contributor line and next contributor descriptor (if more than one contributor descriptor)
LEAGUE_SPARTAN_KERNING = 5 # In px
LEAGUE_SPARTAN_AVERAGE_SPACING = 7 # Guess at average default spacing between letters, in px
LEAGUE_SPARTAN_100_WIDTHS = {" ": 40.0, "A": 98.245, "B": 68.1875, "C": 83.97625, "D": 76.60875, "E": 55.205, "F": 55.79, "G": 91.57875, "H": 75.0875, "I": 21.98875, "J": 52.631254, "K": 87.83625, "L": 55.205, "M": 106.9, "N": 82.5725, "O": 97.1925, "P": 68.1875, "Q": 98.83, "R": 79.41599, "S": 72.63125, "T": 67.83625, "U": 75.32125, "V": 98.245, "W": 134.62, "X": 101.28625, "Y": 93.1, "Z": 86.19875, ".": 26.78375, ",": 26.78375, "/": 66.08125, "\\": 66.08125, "-": 37.66125, ":": 26.78375, ";": 26.78375, "’": 24.3275, "!": 26.78375, "?": 64.3275, "&": 101.87125, "0": 78.48, "1": 37.895, "2": 75.205, "3": 72.04625, "4": 79.29875, "5": 70.175, "6": 74.26875, "7": 76.95875, "8": 72.16375, "9": 74.26875}

class SeError(Exception):
	"""
	Wrapper class for SE exceptions
	"""

	pass

def natural_sort(list_to_sort: list) -> list:
	"""
	Natural sort a list.
	"""

	convert = lambda text: int(text) if text.isdigit() else text.lower()
	alphanum_key = lambda key: [convert(c) for c in regex.split('([0-9]+)', key)]

	return sorted(list_to_sort, key=alphanum_key)

def natural_sort_key(text: str, _nsre=regex.compile('([0-9]+)')):
	"""
	Helper function for sorted() to sort by key.
	"""

	return [int(text) if text.isdigit() else text.lower() for text in regex.split(_nsre, text)]

def replace_in_file(absolute_path: str, search: Union[str, list], replace: Union[str, list]) -> None:
	"""
	Helper function to replace in a file.
	"""

	with open(absolute_path, "r+", encoding="utf-8") as file:
		data = file.read()
		processed_data = data

		if isinstance(search, list):
			for index, val in enumerate(search):
				if replace[index] is not None:
					processed_data = processed_data.replace(val, replace[index])
		else:
			processed_data = processed_data.replace(search, replace)

		if processed_data != data:
			file.seek(0)
			file.write(processed_data)
			file.truncate()

def strip_bom(string: str) -> str:
	"""
	Remove the Unicode Byte Order Mark from a string.

	INPUTS
	string: A Unicode string

	OUTPUTS
	The input string with the Byte Order Mark removed
	"""

	if string.startswith(UNICODE_BOM):
		string = string[1:]

	return string

def quiet_remove(absolute_path: str) -> None:
	"""
	Helper function to delete a file without throwing an exception if the file doesn't exist.
	"""

	try:
		os.remove(absolute_path)
	except Exception:
		pass

def print_error(message: str, verbose: bool = False) -> None:
	"""
	Helper function to print a colored error message to the console.
	"""

	print("{}{} {}".format(MESSAGE_INDENT if verbose else "", colored("Error:", "red", attrs=["reverse"]), message), file=sys.stderr)

def print_warning(message: str, verbose: bool = False) -> None:
	"""
	Helper function to print a colored warning message to the console.
	"""

	print("{}{} {}".format(MESSAGE_INDENT if verbose else "", colored("Warning:", "yellow", attrs=["reverse"]), message))

def print_table(table_data: list, wrap_column: bool = None) -> None:

	"""
	Helper function to print a table to the console.

	INPUTS
	table_data: A list where each entry is a list representing the columns in a table
	wrap_column: The 0-indexed column to wrap

	OUTPUTS
	None
	"""

	table = terminaltables.SingleTable(table_data)
	table.inner_heading_row_border = False
	table.inner_row_border = True
	table.justify_columns[0] = "center"

	# Calculate newlines
	if wrap_column is not None:
		max_width = table.column_max_width(wrap_column)
		for row in table_data:
			row[wrap_column] = '\n'.join(wrap(row[wrap_column], max_width))

	print(table.table)
