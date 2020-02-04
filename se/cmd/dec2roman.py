"""
dec2roman command
"""

import argparse
import sys

import roman

from se.common import is_positive_integer


def cmd_dec2roman() -> int:
	"""
	Entry point for `se dec2roman`
	"""

	parser = argparse.ArgumentParser(description="Convert a decimal number to a Roman numeral.")
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="don’t end output with a newline")
	parser.add_argument("numbers", metavar="INTEGER", type=is_positive_integer, nargs="*", help="an integer")
	args = parser.parse_args()

	lines = []

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
