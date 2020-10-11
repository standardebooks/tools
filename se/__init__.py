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

from rich.console import Console
from rich.text import Text
from rich.theme import Theme
from natsort import natsorted, ns
import regex

VERSION = "1.6.3"
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
# The `re` namespace enables regex functions in xpaths in lxml
XHTML_NAMESPACES = {"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops", "z3998": "http://www.daisy.org/z3998/2012/vocab/structure/", "se": "https://standardebooks.org/vocab/1.0", "dc": "http://purl.org/dc/elements/1.1/", "opf": "http://www.idpf.org/2007/opf", "container": "urn:oasis:names:tc:opendocument:xmlns:container", "m": "http://www.w3.org/1998/Math/MathML", "re": "http://exslt.org/regular-expressions"}
SELECTORS_TO_SIMPLIFY = [":first-child", ":only-child", ":last-child", ":nth-child", ":nth-last-child", ":first-of-type", ":only-of-type", ":last-of-type", ":nth-of-type", ":nth-last-of-type"]
MESSAGE_TYPE_WARNING = 1
MESSAGE_TYPE_ERROR = 2
COVER_HEIGHT = 2100
COVER_WIDTH = 1400
TITLEPAGE_WIDTH = 1400
RICH_THEME = Theme({
	"xhtml": "bright_blue",
	"xml": "bright_blue",
	"val": "bright_blue",
	"attr": "bright_blue",
	"class": "bright_blue",
	"path": "bright_blue",
	"url": "bright_blue",
	"text": "bright_blue",
	"bash": "bright_blue",
	"css": "bright_blue"
})

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

class InvalidSvgException(SeException):
	""" Invalid SVG """
	code = 15

class InvalidXmlException(SeException):
	""" Invalid XHTML """
	code = 16

class BuildFailedException(SeException):
	""" Build failed """
	code = 17

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

	Allowed BBCode tags:
	[link=foo]bar[/] - Hyperlink
	[xml] - XML, usually a tag
	[xhtml] - XHTML, usually a tag
	[attr] - A lone XHTML attribute name (without `="foo"`)
	[val] - A lone XHTML attribute value (not a class)
	[class] - A lone XHTML class value
	[path] - Filesystem path or glob
	[url] - A URL
	[text] - Non-semantic text that requires color
	[bash] - A command or flag of a command
	"""

	label = "Error" if not is_warning else "Warning"
	bg_color = 'red' if not is_warning else 'yellow'

	# We have to print to stdout in case we're called from GNU Parallel, otherwise weird newline issues occur
	# This no longer works with rich because it can't (yet) output to stderr
	output_file = sys.stderr if not is_warning and not is_called_from_parallel() else sys.stdout

	message = str(message)

	if verbose:
		message = str(message).replace("\n", f"\n{MESSAGE_INDENT}")

	console = Console(file=output_file, highlight=False, theme=RICH_THEME, force_terminal=is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel
	console.print(f"{MESSAGE_INDENT if verbose else ''}[white on {bg_color} bold] {label} [/] {message}")

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

	return natsorted(list(target_xhtml_filenames), key=lambda x: str(x.name), alg=ns.PATH)

def is_called_from_parallel() -> bool:
	"""
	Decide if we're being called from GNU parallel.
	This is good to know in case we want to tweak some output.
	"""

	import psutil # pylint: disable=import-outside-toplevel

	try:
		for line in psutil.Process(psutil.Process().ppid()).cmdline():
			if regex.search(fr"{os.sep}parallel$", line):
				return True
	except:
		# If we can't figure it out, don't worry about it
		pass

	return False
