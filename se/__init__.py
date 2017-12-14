#!/usr/bin/env python3

import sys
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
BINARY_EXTENSIONS = [".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".png", ".epub", ".epub3"]
SE_GENRES = ["Adventure", "Autobiography", "Biography", "Childrens", "Comedy", "Drama", "Fantasy", "Fiction", "Horror", "Memoir", "Mystery", "Nonfiction", "Philosophy", "Poetry", "Romance", "Satire", "Science Fiction", "Shorts", "Spirituality", "Tragedy", "Travel"]
MESSAGE_TYPE_WARNING = 1
MESSAGE_TYPE_ERROR = 2
TITLEPAGE_KERNING = 5
TITLEPAGE_AVERAGE_SPACING = 7 # Guess at average default spacing between letters
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
LEAGUE_SPARTAN_80_WIDTHS = {" ": 40, "A": 78.596, "B": 54.550, "C": 67.181, "D": 61.287, "E": 44.164, "F": 44.632, "G": 73.263, "H": 60.070, "I": 17.591, "J": 42.105, "K": 70.269, "L": 44.164, "M": 85.520, "N": 66.058, "O": 77.754, "P": 54.550, "Q": 79.064, "R": 63.532, "S": 58.105, "T": 54.269, "U": 60.257, "V": 78.596, "W": 107.696, "X": 81.029, "Y": 74.480, "Z": 68.959, ".": 21.427, ",": 21.427, "/": 52.865, "\\": 52.865, "-": 30.129, ":": 21.427, ";": 21.427, "’": 19.462, "!": 21.427, "?": 51.462, "&": 81.497, "0": 62.784, "1": 30.316, "2": 60.164, "3": 57.637, "4": 63.439, "5": 56.140, "6": 59.415, "7": 61.567, "8": 57.731, "9": 59.415}
TITLEPAGE_LEAGUE_SPARTAN_60_RATIO = 1.333333
TITLEPAGE_LEAGUE_SPARTAN_40_RATIO = 2

class SeError(Exception):
	pass

def natural_sort(list_to_sort):
	convert = lambda text: int(text) if text.isdigit() else text.lower()
	alphanum_key = lambda key: [convert(c) for c in regex.split('([0-9]+)', key)]
	return sorted(list_to_sort, key=alphanum_key)

def natural_sort_key(text, _nsre=regex.compile('([0-9]+)')):
	return [int(text) if text.isdigit() else text.lower() for text in regex.split(_nsre, text)]

def replace_in_file(filename, search, replace):
	with open(filename, "r+", encoding="utf-8") as file:
		data = file.read()
		file.seek(0)

		if isinstance(search, list):
			for index, val in enumerate(search):
				if replace[index] is not None:
					data = data.replace(val, replace[index])
			file.write(data)
		else:
			file.write(data.replace(search, replace))

		file.truncate()

def print_error(message, verbose=False):
	print("{}{} {}".format(MESSAGE_INDENT if verbose else "", colored("Error:", "red", attrs=["reverse"]), message), file=sys.stderr)

def print_warning(message, verbose=False):
	print("{}{} {}".format(MESSAGE_INDENT if verbose else "", colored("Warning:", "yellow", attrs=["reverse"]), message))

# wrap_column is the 0-indexed column to wrap
def print_table(table_data, wrap_column=None):
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
