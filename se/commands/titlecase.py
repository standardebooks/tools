"""
This module implements the `se titlecase` command.
"""

import argparse
import sys

import se
from se.se_help_formatter import SeHelpFormatter
import se.formatting


def titlecase(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se titlecase`.
	"""

	parser = argparse.ArgumentParser(description="Convert a string to titlecase.", prog="[command]se[/] [subcommand]titlecase[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="Don’t end output with a newline.")
	parser.add_argument("titles", metavar="STRING", nargs="+", help="A string.")
	args = parser.parse_args()

	lines: list[str] = []

	if not sys.stdin.isatty():
		for line in sys.stdin:
			lines.append(line.rstrip("\r\n"))

	for line in args.titles:
		lines.append(line)

	for line in lines:
		if args.newline:
			print(se.formatting.titlecase(line))
		else:
			print(se.formatting.titlecase(line), end="")

	return 0
