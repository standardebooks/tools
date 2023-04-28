"""
This module implements the `se unicode-names` command.
"""

import argparse
import sys
import urllib
import unicodedata

from rich import box
from rich.console import Console
from rich.table import Table

import se

def unicode_names(plain_output: bool) -> int:
	"""
	Entry point for `se unicode-names`
	"""

	parser = argparse.ArgumentParser(description="Display Unicode code points, descriptions, and links to more details for each character in a string. Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.")
	parser.add_argument("strings", metavar="STRING", nargs="*", help="a Unicode string")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME) # Syntax highlighting will do weird things when printing paths
	lines = []

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.strings:
		lines.append(line)

	if plain_output:
		for line in lines:
			for character in line:
				console.print(character, "\tU+{:04X}".format(ord(character)), "\t", unicodedata.name(character)) # pylint: disable=consider-using-f-string
	else:
		table = Table(show_header=False, show_lines=True, box=box.HORIZONTALS)
		table.add_column("Character", style="bold", width=1, no_wrap=True)
		table.add_column("Code point", style="dim", no_wrap=True)
		table.add_column("Description")
		table.add_column("Link")

		for line in lines:
			for character in line:
				try:
					character_name = unicodedata.name(character)
					table.add_row(character, "U+{:04X}".format(ord(character)), character_name, f"[link=https://util.unicode.org/UnicodeJsps/character.jsp?a={urllib.parse.quote_plus(character)}]Properties page[/]") # pylint: disable=consider-using-f-string
				except Exception:
					table.add_row("[white on red bold]?[/]", "U+{:04X}".format(ord(character)), "[white on red bold]Unrecognized[/]", "") # pylint: disable=consider-using-f-string

		console.print(table)

	return 0
