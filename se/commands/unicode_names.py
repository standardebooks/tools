"""
This module implements the `se unicode-names` command.
"""

import argparse
import sys
import unicodedata

from rich import box
from rich.console import Console
from rich.table import Table

import se

def unicode_names() -> int:
	"""
	Entry point for `se unicode-names`
	"""

	parser = argparse.ArgumentParser(description="Display Unicode code points, descriptions, and links to more details for each character in a string. Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.")
	parser.add_argument("strings", metavar="STRING", nargs="*", help="a Unicode string")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME) # Syntax highlighting will do weird things when printing paths
	lines = []
	table = Table(show_header=False, show_lines=True, box=box.HORIZONTALS)

	table.add_column("Character", style="bold", width=1, no_wrap=True)
	table.add_column("Code point", style="dim", no_wrap=True)
	table.add_column("Description")
	table.add_column("Link")

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.strings:
		lines.append(line)

	for line in lines:
		for character in line:
			table.add_row(f"{character}", "U+{:04X}".format(ord(character)), unicodedata.name(character), "[link=https://www.fileformat.info/info/unicode/char/{:04X}]Properties page[/]".format(ord(character)))

	console.print(table)

	return 0
