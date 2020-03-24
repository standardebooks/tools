#!/usr/bin/env python3
"""
Defines various package-level constants and helper functions.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Set, Union

from colored import stylize, fg, bg, attr
from natsort import natsorted
import regex

VERSION = "1.3.0"
MESSAGE_INDENT = "    "
UNICODE_BOM = "\ufeff"
NO_BREAK_SPACE = "\u00a0"
WORD_JOINER = "\u2060"
HAIR_SPACE = "\u200a"
ZERO_WIDTH_SPACE = "\ufeff"
SHY_HYPHEN = "\u00ad"
FUNCTION_APPLICATION = "\u2061"
NO_BREAK_HYPHEN = "\u2011"
IGNORED_FILENAMES = ["colophon.xhtml", "titlepage.xhtml", "imprint.xhtml", "uncopyright.xhtml", "halftitle.xhtml", "toc.xhtml", "loi.xhtml"]
XHTML_NAMESPACES = {"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops", "z3998": "http://www.daisy.org/z3998/2012/vocab/structure/", "se": "https://standardebooks.org/vocab/1.0", "dc": "http://purl.org/dc/elements/1.1/", "opf": "http://www.idpf.org/2007/opf", "container": "urn:oasis:names:tc:opendocument:xmlns:container", "m": "http://www.w3.org/1998/Math/MathML"}
FRONTMATTER_FILENAMES = ["dedication.xhtml", "introduction.xhtml", "preface.xhtml", "foreword.xhtml", "preamble.xhtml", "titlepage.xhtml", "halftitlepage.xhtml", "imprint.xhtml"]
BACKMATTER_FILENAMES = ["endnotes.xhtml", "loi.xhtml", "afterword.xhtml", "appendix.xhtml", "colophon.xhtml", "uncopyright.xhtml"]
BINARY_EXTENSIONS = [".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".png", ".epub", ".epub3", ".xcf", ".otf"]
SE_GENRES = ["Adventure", "Autobiography", "Biography", "Childrens", "Comedy", "Drama", "Fantasy", "Fiction", "Horror", "Memoir", "Mystery", "Nonfiction", "Philosophy", "Poetry", "Romance", "Satire", "Science Fiction", "Shorts", "Spirituality", "Tragedy", "Travel"]
ARIA_ROLES = ["afterword", "appendix", "biblioentry", "bibliography", "chapter", "colophon", "conclusion", "dedication", "epilogue", "foreword", "introduction", "noteref", "part", "preface", "prologue", "subtitle", "toc"]
IGNORED_CLASSES = ["name", "temperature", "state", "era", "compass", "acronym", "postal", "eoc", "initialism", "degree", "time", "compound", "timezone", "signature", "full-page"]
SELECTORS_TO_SIMPLIFY = [":first-child", ":only-child", ":last-child", ":nth-child", ":nth-last-child", ":first-of-type", ":only-of-type", ":last-of-type", ":nth-of-type", ":nth-last-of-type"]
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
NOVELLA_MIN_WORD_COUNT = 17500
NOVEL_MIN_WORD_COUNT = 40000

class SeException(Exception):
	""" Wrapper class for SE exceptions """

	code = 0

# Note that we skip error codes 1 and 2 as they have special meanings:
# http://www.tldp.org/LDP/abs/html/exitcodes.html

class InvalidXhtmlException(SeException):
	""" Invalid XHTML """
	code = 3

class InvalidEncodingException(SeException):
	""" Invalid encoding """
	code = 4

class MissingDependencyException(SeException):
	""" Missing dependency """
	code = 5

class InvalidInputException(SeException):
	""" Invalid input """
	code = 6

class FileExistsException(SeException):
	""" File exists """
	code = 7

class InvalidFileException(SeException):
	""" Invalid file """
	code = 8

class InvalidLanguageException(SeException):
	""" Invalid language """
	code = 9

class InvalidSeEbookException(SeException):
	""" Invalid SE ebook """
	code = 10

class InvalidArgumentsException(SeException):
	""" Invalid arguments """
	code = 11

class RemoteCommandErrorException(SeException):
	""" Error in remote command """
	code = 12

class LintFailedException(SeException):
	""" Lint failed """
	code = 13

class InvalidCssException(SeException):
	""" Invalid CSS """
	code = 14

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

def quiet_remove(file: Path) -> None:
	"""
	Helper function to delete a file without throwing an exception if the file doesn't exist.
	"""

	try:
		file.unlink()
	except Exception:
		pass

def print_error(message: Union[SeException, str], verbose: bool = False, is_warning: bool = False) -> None:
	"""
	Helper function to print a colored error message to the console.
	"""

	label = "Error" if not is_warning else "Warning"
	bg_color = 'red_3a' if not is_warning else 'yellow'
	output_file = sys.stderr if not is_warning else sys.stdout

	# By convention, any text within the message text that is surrounded in backticks
	# is rendered in blue
	message = regex.sub(r"`(.+?)`", stylize(r"\1", fg("light_blue")), message)

	print(f"{MESSAGE_INDENT if verbose else ''}{stylize(f' {label} ', bg(bg_color) + fg('white') + attr('bold'))} {message}", file=output_file)

def is_positive_integer(value: str) -> int:
	"""
	Helper function for argparse.
	Raise an exception if value is not a positive integer.
	"""

	int_value = int(value)
	if int_value <= 0:
		raise argparse.ArgumentTypeError(f"{value} is not a positive integer")

	return int_value

def get_target_filenames(targets: list, allowed_extensions: tuple, ignored_filenames: list = None) -> list:
	"""
	Helper function to convert a list of filenames or directories into a list of filenames based on some parameters.

	INPUTS
	targets: A list of filenames or directories
	allowed_extensions: A tuple containing a series of allowed filename extensions; extensions must begin with "."
	ignored_filenames: If None, ignore files in the se.IGNORED_FILENAMES constant. If a list, ignore that list of filenames.
				Pass an empty list to ignore no files.

	OUTPUTS
	A set of file paths and filenames contained in the target list.
	"""

	if ignored_filenames is None:
		ignored_filenames = IGNORED_FILENAMES

	target_xhtml_filenames = set()

	for target in targets:
		target = Path(target).resolve()

		if target.is_dir():
			for root, _, filenames in os.walk(target):
				for filename in filenames:
					if allowed_extensions:
						if filename.endswith(allowed_extensions):
							if filename not in ignored_filenames:
								target_xhtml_filenames.add(Path(root) / filename)
					else:
						if filename not in ignored_filenames:
							target_xhtml_filenames.add(Path(root) / filename)
		else:
			if target.name.endswith(allowed_extensions):
				target_xhtml_filenames.add(target)

	return natsorted(list(target_xhtml_filenames))
