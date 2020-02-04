"""
Common utility functions
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from textwrap import wrap
from typing import Set, Union

import regex
import terminaltables
from termcolor import colored

import se


def version() -> str:
	"""
	Returns the version string for the standardebooks package
	"""

	# This import is slow, so only do it for this function
	import pkg_resources  # pylint: disable=import-outside-toplevel

	try:
		return pkg_resources.get_distribution("standardebooks").version
	except Exception:
		# we get in this branch when the package hasn't been installed via pip or
		# the setup script.
		return "unknown"

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

def replace_in_file(file_path: Path, search: Union[str, list], replace: Union[str, list]) -> None:
	"""
	Helper function to replace in a file.
	"""

	with open(file_path, "r+", encoding="utf-8") as file:
		data = file.read()
		processed_data = data

		if isinstance(search, list):
			for index, val in enumerate(search):
				if replace[index] is not None:
					processed_data = processed_data.replace(val, replace[index])
		else:
			processed_data = processed_data.replace(search, str(replace))

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

	if string.startswith(se.UNICODE_BOM):
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

def print_error(message: Union[se.SeException, str], verbose: bool = False) -> None:
	"""
	Helper function to print a colored error message to the console.
	"""

	print("{}{} {}".format(se.MESSAGE_INDENT if verbose else "", colored("Error:", "red", attrs=["reverse"]), message), file=sys.stderr)

def print_warning(message: str, verbose: bool = False) -> None:
	"""
	Helper function to print a colored warning message to the console.
	"""

	print("{}{} {}".format(se.MESSAGE_INDENT if verbose else "", colored("Warning:", "yellow", attrs=["reverse"]), message))

def print_table(table_data: list, wrap_column: int = None) -> None:
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

def is_positive_integer(value: str) -> int:
	"""
	Helper function for argparse.
	Raise an exception if value is not a positive integer.
	"""

	int_value = int(value)
	if int_value <= 0:
		raise argparse.ArgumentTypeError(f"{value} is not a positive integer")

	return int_value

def get_target_filenames(targets: list, allowed_extensions: tuple, ignored_filenames: list = None) -> Set[Path]:
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
		ignored_filenames = se.IGNORED_FILENAMES

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

	return target_xhtml_filenames

def get_firefox_path() -> Path:
	"""
	Get the path to the local Firefox binary
	"""

	which_firefox = shutil.which("firefox")
	if which_firefox:
		firefox_path = Path(which_firefox)
	else:
		# Look for default mac Firefox.app path if none found in path
		firefox_path = Path("/Applications/Firefox.app/Contents/MacOS/firefox")
		if not firefox_path.exists():
			raise se.MissingDependencyException("Couldn’t locate firefox. Is it installed?")

	return firefox_path
