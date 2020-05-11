"""
This module implements the `se roman2dec` command.
"""

import argparse
import sys

import roman

import se


def roman2dec() -> int:
	"""
	Entry point for `se roman2dec`
	"""

	parser = argparse.ArgumentParser(description="Convert a Roman numeral to a decimal number.")
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="don’t end output with a newline")
	parser.add_argument("numbers", metavar="NUMERAL", nargs="+", help="a Roman numeral")
	args = parser.parse_args()

	lines = []

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.numbers:
		lines.append(line)

	for line in lines:
		try:
			if args.newline:
				print(roman.fromRoman(line.upper()))
			else:
				print(roman.fromRoman(line.upper()), end="")
		except roman.InvalidRomanNumeralError:
			se.print_error(f"Not a Roman numeral: [text]{line}[/]")
			return se.InvalidInputException.code

	return 0
