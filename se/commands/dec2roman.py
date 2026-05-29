"""
This module implements the `se dec2roman` command.
"""

import argparse
import sys

import roman

import se
from se.se_help_formatter import SeHelpFormatter


def dec2roman(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se dec2roman`.
	"""

	parser = argparse.ArgumentParser(description="Convert a decimal number to a Roman numeral.", formatter_class=SeHelpFormatter)
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="Don’t end output with a newline.")
	parser.add_argument("numbers", metavar="INTEGER", type=se.is_positive_integer, nargs="*", help="An integer.")
	args = parser.parse_args()

	lines: list[str] = []

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.numbers:
		lines.append(line)

	for line in lines:
		if args.newline:
			print(roman.toRoman(int(line)))
		else:
			print(roman.toRoman(int(line)), end="")

	return 0
