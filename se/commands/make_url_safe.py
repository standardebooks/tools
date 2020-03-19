"""
This module implements the `se make-url-safe` command.
"""

import argparse
import sys

import se
import se.formatting


def make_url_safe() -> int:
	"""
	Entry point for `se make-url-safe`
	"""

	parser = argparse.ArgumentParser(description="Make a string URL-safe.")
	parser.add_argument("-n", "--no-newline", dest="newline", action="store_false", help="don’t end output with a newline")
	parser.add_argument("strings", metavar="STRING", nargs="*", help="a string")
	args = parser.parse_args()

	lines = []

	if not sys.stdin.isatty():
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
