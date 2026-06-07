"""
This module implements the `se make-url-safe` command.
"""

import argparse
import sys

import se
from se.se_help_formatter import SeHelpFormatter
import se.formatting


def make_url_safe(plain_output: bool) -> int: # pylint: disable=unused-argument
	"""
	Entry point for `se make-url-safe`.
	"""

	is_stdin_pipe = not sys.stdin.isatty()

	parser = argparse.ArgumentParser(description="Make a string URL-safe.", prog="[command]se[/] [subcommand]make-url-safe[/]", formatter_class=SeHelpFormatter)
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="Don’t end output with a newline.")
	parser.add_argument("strings", metavar="STRING", nargs="*" if is_stdin_pipe else "+", help="A string.")
	args = parser.parse_args()

	lines: list[str] = []

	if is_stdin_pipe:
		for line in sys.stdin:
			lines.append(line.rstrip("\n"))

	for line in args.strings:
		lines.append(line)

	for line in lines:
		if args.newline:
			print(se.formatting.make_url_safe(line))
		else:
			print(se.formatting.make_url_safe(line), end="")

	return 0
