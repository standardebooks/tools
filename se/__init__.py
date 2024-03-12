#!/usr/bin/env python3
"""
Defines various package-level constants and helper functions.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Union, List, Tuple, Optional

from rich.console import Console
from rich.theme import Theme
from natsort import natsorted, ns
import regex

import se.easy_xml

VERSION = "2.6.3"
MESSAGE_INDENT = "    "
UNICODE_BOM = "\ufeff"
NO_BREAK_SPACE = "\u00a0"
WORD_JOINER = "\u2060"
HAIR_SPACE = "\u200a"
ZERO_WIDTH_SPACE = "\ufeff"
SHY_HYPHEN = "\u00ad"
FUNCTION_APPLICATION = "\u2061"
NO_BREAK_HYPHEN = "\u2011"
COMBINING_VERTICAL_LINE_ABOVE = "\u030d"
COMBINING_ACUTE_ACCENT = "\u0301"
INVISIBLE_TIMES = "\u2062"
SELECTORS_TO_SIMPLIFY = [":first-child", ":only-child", ":last-child", ":nth-child", ":nth-last-child", ":first-of-type", ":only-of-type", ":last-of-type", ":nth-of-type", ":nth-last-of-type", ":empty"]
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

	def __init__(self, message, messages: Optional[List] = None):
		super().__init__(message)
		self.messages = messages if messages else []

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

def prep_output(message: str, plain_output: bool = False) -> str:
	"""
	Return a message formatted for the chosen output style, i.e., color or plain.
	"""

	if plain_output:
		# Replace color markup with `
		message = regex.sub(r"\[(?:/|xhtml|xml|val|attr|css|val|class|path|url|text|bash|link)(?:=[^\]]*?)*\]", "`", message)
		message = regex.sub(r"`+", "`", message)

	return message

def print_error(message: Union[SeException, str], verbose: bool = False, is_warning: bool = False, plain_output: bool = False) -> None:
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
	bg_color = "red" if not is_warning else "yellow"

	# We have to print to stdout in case we're called from GNU Parallel, otherwise weird newline issues occur
	# This no longer works with rich because it can't (yet) output to stderr
	output_file = sys.stderr if not is_warning and not is_called_from_parallel() else sys.stdout

	message = str(message)

	if verbose:
		message = str(message).replace("\n", f"\n{MESSAGE_INDENT}")

	console = Console(file=output_file, highlight=False, theme=RICH_THEME, force_terminal=is_called_from_parallel()) # Syntax highlighting will do weird things when printing paths; force_terminal prints colors when called from GNU Parallel

	if plain_output:
		# Replace color markup with `
		message = prep_output(message, True)
		console.print(f"{MESSAGE_INDENT if verbose else ''}[{label}] {message}")
	else:
		console.print(f"{MESSAGE_INDENT if verbose else ''}[white on {bg_color} bold] {label} [/] {message}")

def is_positive_integer(value: str) -> int:
	"""
	Helper function for argparse.
	Raise an exception if value is not a positive integer.
	"""

	try:
		int_value = int(value)
		if int_value <= 0:
			raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
	except Exception as ex:
		raise argparse.ArgumentTypeError(f"{value} is not a positive integer") from ex

	return int_value

def get_target_filenames(targets: list, allowed_extensions: Union[tuple, str]) -> list:
	"""
	Helper function to convert a list of filenames or directories into a list of filenames based on some parameters.

	allowed_extensions is only applied on targets that are directories.

	INPUTS
	targets: A list of filenames or directories
	allowed_extensions: A tuple containing a series of allowed filename extensions; extensions must begin with "."

	OUTPUTS
	A set of file paths and filenames contained in the target list.
	"""

	target_xhtml_filenames = set()

	if isinstance(allowed_extensions, str):
		allowed_extensions = (allowed_extensions,)

	for target in targets:
		target = Path(target).resolve()

		if target.is_dir():
			for file_path in target.glob("**/*"):
				file_path.resolve()
				if allowed_extensions:
					if file_path.suffix in allowed_extensions:
						target_xhtml_filenames.add(file_path)
				else:
					target_xhtml_filenames.add(file_path)
		else:
			# If we're looking at an actual file, just add it regardless of whether it's ignored
			target_xhtml_filenames.add(target)

	return natsorted(list(target_xhtml_filenames), key=lambda x: str(x.name), alg=ns.PATH)

def is_called_from_parallel(return_none=True) -> Union[bool,None]:
	"""
	Decide if we're being called from GNU parallel.
	This is good to know in case we want to tweak some output.

	This is almost always passed directly to the force_terminal option of rich.console(),
	meaning that `None` means "guess terminal status" and `False` means "no colors at all".
	We typically want to guess, so this returns None by default if not called from Parallel.
	To return false in that case, pass return_none=False
	"""

	import psutil # pylint: disable=import-outside-toplevel

	try:
		for line in psutil.Process(psutil.Process().ppid()).cmdline():
			if regex.search(fr"{os.sep}parallel$", line):
				return True
	except Exception:
		# If we can't figure it out, don't worry about it
		pass

	return None if return_none else False

def get_dom_if_not_ignored(xhtml: str, ignored_types: Union[List[str],None] = None) -> Tuple[bool, Union[None, se.easy_xml.EasyXmlTree]]:
	"""
	Given a string of XHTML, return a dom tree ONLY IF the dom does not contain a
	top-level <section> element with any of the passed semantics.

	Pass an empty list to ignored_types to ignore nothing.
	Pass None to ignored_types to ignore a default set of SE files.

	RETURNS
	A tuple of (is_ignored, dom)
	If the file is ignored, is_ignored will be True.
	If the dom couldn't be created (for example it is invalid XML) then the dom part
	of the tuple will be None.
	"""

	is_ignored = False
	ignored_regex = None
	dom = None

	try:
		dom = se.easy_xml.EasyXmlTree(xhtml)
	except Exception:
		return (False, None)

	# Ignore some SE files
	# Default ignore list
	if ignored_types is None:
		ignored_regex = "(colophon|titlepage|imprint|copyright-page|halftitlepage|toc|loi)"

	elif len(ignored_types) > 0:
		ignored_regex = "("
		for item in ignored_types:
			ignored_regex = f"{ignored_regex}{regex.escape(item)}|"

		ignored_regex = ignored_regex.rstrip("|") + ")"

	if ignored_regex:
		if dom.xpath(f"/html[re:test(@epub:prefix, '[\\s\\b]se:[\\s\\b]')]/body/*[(name() = 'section' or name() = 'nav') and re:test(@epub:type, '\\b{ignored_regex}\\b')]"):
			is_ignored = True

	return (is_ignored, dom)
