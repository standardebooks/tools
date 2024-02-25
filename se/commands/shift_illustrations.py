"""
This module implements the `se shift-illustrations` command.
"""

import argparse

import se
from se.se_epub import SeEpub


def shift_illustrations(plain_output: bool) -> int:
	"""
	Entry point for `se shift-illustrations`
	"""

	parser = argparse.ArgumentParser(description="Increment or decrement the specified illustration and all following illustrations by 1 or a specified amount.")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("-d", "--decrement", action="store_true", help="decrement the target illustration number and all following illustrations")
	group.add_argument("-i", "--increment", action="store_true", help="increment the target illustration number and all following illustrations")
	parser.add_argument("-a", "--amount", metavar="NUMBER", dest="amount", default=1, type=se.is_positive_integer, help="the amount to increment or decrement by; defaults to 1")
	parser.add_argument("target_illustration_number", metavar="ILLUSTRATION-NUMBER", type=se.is_positive_integer, help="the illustration number to start shifting at")
	parser.add_argument("directory", metavar="DIRECTORY", help="a Standard Ebooks source directory")
	args = parser.parse_args()

	return_code = 0

	try:
		if args.increment:
			step = args.amount
		else:
			step = args.amount * -1

		se_epub = SeEpub(args.directory)
		se_epub.shift_illustrations(args.target_illustration_number, step)

	except se.SeException as ex:
		se.print_error(ex, plain_output=plain_output)
		return_code = ex.code

	return return_code
