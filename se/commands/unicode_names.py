"""
This module implements the `se unicode-names` command.
"""

import argparse
import sys
import unicodedata


def unicode_names() -> int:
	"""
	Entry point for `se unicode-names`
	"""

	parser = argparse.ArgumentParser(description="Display Unicode code points, descriptions, and links to more details for each character in a string. Useful for differentiating between different flavors of spaces, dashes, and invisible characters like word joiners.")
	parser.add_argument("strings", metavar="STRING", nargs="*", help="a Unicode string")
	args = parser.parse_args()

	lines = []

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.strings:
		lines.append(line)

	for line in lines:
		for character in line:
			print(character + "\tU+{:04X}".format(ord(character)) + "\t" + unicodedata.name(character) + "\t" + "http://unicode.org/cldr/utility/character.jsp?a={:04X}".format(ord(character)))

	return 0
