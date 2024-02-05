"""
This module implements the `se find-unusual-characters` command.
"""

import argparse
from typing import Dict
import unicodedata

import regex
from rich import box
from rich.console import Console
from rich.table import Table

import se

def find_unusual_characters(plain_output: bool) -> int:
	"""
	Entry point for `se find-unusual-characters`
	"""

	parser = argparse.ArgumentParser(description="Find characters outside a nominal expected range in a set of XHTML files. This can be useful to find transcription mistakes and mojibake.")
	parser.add_argument("targets", metavar="TARGET", nargs="+", help="an XHTML file, or a directory containing XHTML files")
	args = parser.parse_args()

	console = Console(highlight=False, theme=se.RICH_THEME) # Syntax highlighting will do weird things when printing paths
	return_code = 0
	unusual_characters: Dict[str, int] = {} # key: word; value: count
	target_filenames = se.get_target_filenames(args.targets, ".xhtml")
	files_xhtml = []

	# Read files and cache for later
	for filename in target_filenames:
		try:
			with open(filename, "r", encoding="utf-8") as file:
				xhtml = file.read()
				dom = se.easy_xml.EasyXmlTree(xhtml)

				# Save any `alt` and `title` attributes because we may be interested in their contents
				for node in dom.xpath("//*[@alt or @title]"):
					for _, value in node.attrs.items():
						xhtml = xhtml + f" {value} "

				# Strip tags
				xhtml = regex.sub(r"<[^>]+?>", " ", xhtml)

				files_xhtml.append(xhtml)

		except FileNotFoundError:
			se.print_error(f"Couldn’t open file: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = se.InvalidInputException.code

		except se.SeException as ex:
			se.print_error(str(ex) + f" File: [path][link=file://{filename}]{filename}[/][/].", plain_output=plain_output)
			return_code = ex.code

	# Create a regex for unusual characters.
	# The result is a series of Unicode ranges that cover the characters
	# we _don’t_ expect to see in a standard SE production. The comments
	# indicate the Unicode ranges we exclude from the regex as they’re
	# normal characters we don’t want to flag.

	unusual_character_set = "["
	# OK: basic ASCII u0000-u007e
	unusual_character_set += "\u007f-\u009f"
	# OK: NO BREAK SPACE u00a0
	unusual_character_set += "\u00a1"
	# OK: CENT SIGN and POUND SIGN u00a2-u00a3
	unusual_character_set += "\u00a4-\u00af"
	# OK: DEGREE SYMBOL u00b0
	unusual_character_set += "\u00b1-\u00b6"
	# OK: MIDDLE DOT u00b7 (used for Morse code)
	unusual_character_set += "\u00b8-\u00bb"
	# OK: vulgar fractions u00bc-u00be
	unusual_character_set += "\u00bf"
	# OK: standard accented letters u00c0-u00ff
	unusual_character_set += "\u0100-\u0151"
	# OK: œ / Œ u0152-u0153
	unusual_character_set += "\u0154-\u02ba"
	# OK: MODIFIER LETTER TURNED COMMA u02bb (used for glottal stops)
	unusual_character_set += "\u02bc"
	# OK: MODIFIER LETTER REVERSED COMMA u02bd (used for Greek / Chinese)
	unusual_character_set += "\u02be-\u030c"
	# OK: COMBINING VERTICAL LINE ABOVE u030d
	unusual_character_set += "\u030e-\u036f"
	# OK: basic Greek characters u0370-u03ff
	unusual_character_set += "\u0400-\u1eff"
	# OK: extended Greek characters u1f00-u1fff
	unusual_character_set += "\u2000-\u2009"
	# OK: HAIR SPACE u200a
	unusual_character_set += "\u200b-\u2011"
	# OK: valid dashes u2012-u2014, but no-break hyphen is invalid
	unusual_character_set += "\u2015-\u2017"
	# OK: valid single quotes u2018-u2019
	unusual_character_set += "\u201a-\u201b"
	# OK: valid double quotes u201c-u201d
	unusual_character_set += "\u201e-\u2025"
	# OK: HORIZONTAL ELLIPSIS u2026
	unusual_character_set += "\u2027-\u2031"
	# OK: single/double prime marks u2032-u2033
	unusual_character_set += "\u2034-\u203d"
	# OK: OVERLINE u203e (used in MathML)
	unusual_character_set += "\u203f-\u2043"
	# OK: FRACTION SLASH u2044
	unusual_character_set += "\u2045-\u205f"
	# OK: WORD JOINER u2060
	unusual_character_set += "\u2061-\u21a8"
	# OK: LEFTWARDS ARROW WITH HOOK u21a9 (used in endquotes)
	unusual_character_set += "\u21aa-\u2211"
	# OK: MINUS SIGN u2212
	unusual_character_set += "\u2213-\u2235"
	# OK: RATIO u2236
	unusual_character_set += "\u2237-\u2260"
	# OK: IDENTICAL TO u2261
	unusual_character_set += "\u2262-\u22ed"
	# OK: VERTICAL ELLIPSIS u22ee
	unusual_character_set += "\u22ef-\u2e39"
	# OK: two-/three-em dashes u2e3a-u2e3b
	unusual_character_set += "\u2e3c-\ufefe"
	unusual_character_set += "]"

	for xhtml in files_xhtml:
		for character in regex.findall(unusual_character_set, xhtml):
			if character in unusual_characters:
				unusual_characters[character] = unusual_characters[character] + len(character)
			else:
				unusual_characters[character] = len(character)

	# Sort and prepare the output
	lines = []

	for unusual_character, count in unusual_characters.items():
		lines.append((unusual_character, unicodedata.name(unusual_character), count))

	lines.sort()

	if lines:
		if plain_output:
			for unusual_character, unusual_character_name, unusual_character_count in lines:
				console.print(f"{unusual_character} {unusual_character_name} ({unusual_character_count})")

		else:
			table = Table(show_header=False, show_lines=True, box=box.HORIZONTALS)
			table.add_column("Character", style="bold", width=1, no_wrap=True)
			table.add_column("Code point", style="dim", no_wrap=True)
			table.add_column("Name")
			table.add_column("Count", style="dim", no_wrap=True)

			for unusual_character, unusual_character_name, unusual_character_count in lines:
				table.add_row(unusual_character, "U+{:04X}".format(ord(unusual_character)), unusual_character_name, f"({unusual_character_count})") # pylint: disable=consider-using-f-string

			console.print(table)

	return return_code
