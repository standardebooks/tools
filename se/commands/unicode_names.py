"""
This module implements the `se unicode-names` command.
"""

import argparse
import sys
import urllib.parse
import unicodedata

from rich import box
from rich.table import Table

import se

def unicode_names(plain_output: bool) -> int:
	"""
	Entry point for `se unicode-names`.
	"""

	parser = argparse.ArgumentParser(description="Display Unicode code points, descriptions, and links to more details for each character in a string. Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.")
	parser.add_argument("strings", metavar="STRING", nargs="*", help="a Unicode string")
	args = parser.parse_args()

	console = se.init_console()
	lines = []

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.strings:
		lines.append(line)

	if plain_output:
		for line in lines:
			for character in line:
				# The unicodedata package crashes on characters that don't have a name; see GitHub
				# issue https://github.com/python/cpython/issues/91103
				try:
					character_name = unicodedata.name(character)
				except Exception:
					character_name = "Unrecognized"

				console.print(character, "\tU+{:04X}".format(ord(character)), "\t", character_name) # pylint: disable=consider-using-f-string
	else:
		table = Table(show_header=False, show_lines=True, box=box.HORIZONTALS)
		table.add_column("Character", style="bold", width=1, no_wrap=True)
		table.add_column("Code point", style="dim", no_wrap=True)
		table.add_column("Description")
		table.add_column("Link")

		for line in lines:
			for character in line:
				# The unicodedata package crashes on characters that don't have a name
				try:
					character_name = unicodedata.name(character)
				except Exception:
					character_name = "[white on red bold]Unrecognized[/]"

				table.add_row(character, "U+{:04X}".format(ord(character)), character_name, f"[link=https://util.unicode.org/UnicodeJsps/character.jsp?a={urllib.parse.quote_plus(character)}]Properties page[/]") # pylint: disable=consider-using-f-string

		console.print(table)

	return 0
