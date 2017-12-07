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
